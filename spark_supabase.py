"""
Spark Job: Processa dados do Supabase e grava nas tabelas corretas
Lê eventos do Kafka e detecta o tipo (lead ou chat_session) para gravar na tabela apropriada
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SupabaseSparkJob")

# Inicializar Spark Session
spark = SparkSession.builder \
    .appName("SupabaseToPostgres") \
    .config("spark.jars.packages", 
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
            "org.postgresql:postgresql:42.7.0") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Configurações
KAFKA_BOOTSTRAP = "kafka:29092"
KAFKA_TOPIC = "eventos"
POSTGRES_URL = "jdbc:postgresql://postgres:5432/superset"
POSTGRES_PROPS = {
    "user": "superset",
    "password": "superset",
    "driver": "org.postgresql.Driver"
}

# Schema para leads (completo do Supabase)
leads_schema = StructType([
    StructField("id", StringType(), True),
    StructField("nome", StringType(), True),
    StructField("email", StringType(), True),
    StructField("telefone", StringType(), True),
    StructField("nome_empresa", StringType(), True),
    StructField("nome_projeto", StringType(), True),
    StructField("localizacao", StringType(), True),  # JSON como string
    StructField("interesse", ArrayType(StringType()), True),
    StructField("score_qualificacao", IntegerType(), True),
    StructField("status_lead", StringType(), True),
    StructField("origem", StringType(), True),
    StructField("utm_source", StringType(), True),
    StructField("utm_medium", StringType(), True),
    StructField("utm_campaign", StringType(), True),
    StructField("created_at", StringType(), True),
    StructField("updated_at", StringType(), True),
    StructField("last_interaction_at", StringType(), True),
    StructField("tipo_evento", StringType(), True),
    StructField("processado_em", StringType(), True)
 ])

# Schema para chat_sessions (completo do Supabase)
sessions_schema = StructType([
    StructField("id", StringType(), True),
    StructField("lead_id", StringType(), True),
    StructField("session_token", StringType(), True),
    StructField("user_agent", StringType(), True),
    StructField("ip_address", StringType(), True),
    StructField("total_messages", IntegerType(), True),
    StructField("duration_seconds", IntegerType(), True),
    StructField("pages_visited", ArrayType(StringType()), True),
    StructField("perguntas_feitas", ArrayType(StringType()), True),
    StructField("intencao_detectada", StringType(), True),
    StructField("nivel_interesse", StringType(), True),
    StructField("started_at", StringType(), True),
    StructField("ended_at", StringType(), True),
    StructField("is_active", BooleanType(), True),
    StructField("tipo_evento", StringType(), True),
    StructField("processado_em", StringType(), True)
])

logger.info("🚀 Iniciando Spark Streaming Job - Supabase to Postgres")

# Ler stream do Kafka
df_kafka = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
    .option("subscribe", KAFKA_TOPIC) \
    .option("startingOffsets", "earliest") \
    .option("failOnDataLoss", "false") \
    .load()

# Converter value de bytes para string
df = df_kafka.select(col("value").cast("string").alias("json_data"))

# Parse JSON
df_parsed = df.select(from_json(col("json_data"), 
                                 StructType([
                                     StructField("tipo_evento", StringType(), True),
                                     StructField("id", StringType(), True)
                                 ])).alias("data")) \
              .select("data.*")

def process_batch(batch_df, batch_id):
    """Processa cada batch e grava nas tabelas corretas"""
    logger.info(f"📦 Processando batch #{batch_id}")
    
    #Contar registros
    total_count = batch_df.count()
    if total_count == 0:
        logger.info(" Batch vazio, pulando...")
        return
    
    logger.info(f"📊 Total de registros no batch: {total_count}")
    
    # Separar por tipo
    leads_df = batch_df.filter(col("data.tipo_evento") == "lead") \
                      .select(from_json(col("json_data"), leads_schema).alias("lead")) \
                      .select("lead.*") \
                      .drop("tipo_evento")
    
    sessions_df = batch_df.filter(col("data.tipo_evento") == "chat_session") \
                         .select(from_json(col("json_data"), sessions_schema).alias("session")) \
                         .select("session.*") \
                         .drop("tipo_evento")
    
    # Contar por tipo
    leads_count = leads_df.count()
    sessions_count = sessions_df.count()
    
    logger.info(f"  • Leads: {leads_count}")
    logger.info(f"  • Chat Sessions: {sessions_count}")
    
    # Gravar leads
    if leads_count > 0:
        try:
            logger.info(f"💾 Gravando {leads_count} leads no Postgres...")
            leads_df.write \
                .jdbc(url=POSTGRES_URL, 
                      table="leads", 
                      mode="append", 
                      properties=POSTGRES_PROPS)
            logger.info(f"✅ {leads_count} leads gravados com sucesso!")
        except Exception as e:
            logger.error(f"❌ Erro ao gravar leads: {str(e)}")
    
    # Gravar sessões
    if sessions_count > 0:
        try:
            logger.info(f"💾 Gravando {sessions_count} sessões no Postgres...")
            sessions_df.write \
                .jdbc(url=POSTGRES_URL, 
                      table="chat_sessions", 
                      mode="append", 
                      properties=POSTGRES_PROPS)
            logger.info(f"✅ {sessions_count} sessões gravadas com sucesso!")
        except Exception as e:
            logger.error(f"❌ Erro ao gravar sessões: {str(e)}")
    
    logger.info(f"✅ Batch #{batch_id} processado!")

# Iniciar streaming query
query = df.select(col("json_data")) \
    .writeStream \
    .foreachBatch(process_batch) \
    .outputMode("append") \
    .option("checkpointLocation", "/tmp/spark-checkpoint-supabase") \
    .start()

logger.info("✅ Stream iniciado! Aguardando dados...")

# Aguardar término
query.awaitTermination()
