"""
Pipeline Spark Streaming - Kafka -> Transformações -> Postgres + Elasticsearch
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    from_json, col, current_timestamp, window, count, avg, sum as _sum
)
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType, TimestampType
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurações
KAFKA_BOOTSTRAP_SERVERS = "kafka:9092"
KAFKA_TOPIC = "eventos"
POSTGRES_URL = "jdbc:postgresql://postgres:5432/superset"
POSTGRES_USER = "superset"
POSTGRES_PASSWORD = "superset"
ELASTICSEARCH_HOST = "elasticsearch"
ELASTICSEARCH_PORT = "9200"

# Schema dos dados do Kafka (ajuste conforme seu caso)
schema = StructType([
    StructField("id", StringType(), True),
    StructField("usuario", StringType(), True),
    StructField("evento", StringType(), True),
    StructField("valor", DoubleType(), True),
    StructField("timestamp", TimestampType(), True),
    StructField("categoria", StringType(), True)
])


def criar_spark_session():
    """Cria e configura a sessão Spark"""
    return SparkSession.builder \
        .appName("KafkaSparkPostgresPipeline") \
        .config("spark.jars.packages", 
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
                "org.postgresql:postgresql:42.7.0,"
                "org.elasticsearch:elasticsearch-spark-30_2.12:8.11.0") \
        .config("spark.sql.streaming.checkpointLocation", "/opt/spark-data/checkpoint") \
        .config("spark.streaming.stopGracefullyOnShutdown", "true") \
        .getOrCreate()


def ler_kafka_stream(spark):
    """Lê stream do Kafka"""
    logger.info(f"Conectando ao Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", KAFKA_TOPIC) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()
    
    logger.info("Stream do Kafka conectado com sucesso")
    return df


def transformar_dados(df):
    """Aplica transformações nos dados"""
    logger.info("Aplicando transformações nos dados...")
    
    # Parse do JSON do Kafka
    df_parsed = df.select(
        from_json(col("value").cast("string"), schema).alias("data")
    ).select("data.*")
    
    # Adicionar timestamp de processamento
    df_transformed = df_parsed.withColumn(
        "processado_em", 
        current_timestamp()
    )
    
    logger.info("Transformações aplicadas")
    return df_transformed


def criar_agregacoes(df):
    """Cria agregações por janela de tempo"""
    logger.info("Criando agregações...")
    
    df_agg = df \
        .withWatermark("timestamp", "10 minutes") \
        .groupBy(
            window("timestamp", "5 minutes", "1 minute"),
            "categoria",
            "evento"
        ) \
        .agg(
            count("*").alias("total_eventos"),
            avg("valor").alias("valor_medio"),
            _sum("valor").alias("valor_total")
        ) \
        .select(
            col("window.start").alias("janela_inicio"),
            col("window.end").alias("janela_fim"),
            "categoria",
            "evento",
            "total_eventos",
            "valor_medio",
            "valor_total",
            current_timestamp().alias("processado_em")
        )
    
    return df_agg


def gravar_postgres(df, tabela, modo="append"):
    """Grava dados no Postgres"""
    logger.info(f"Gravando dados na tabela {tabela} do Postgres...")
    
    def write_batch(batch_df, batch_id):
        batch_df.write \
            .format("jdbc") \
            .option("url", POSTGRES_URL) \
            .option("dbtable", tabela) \
            .option("user", POSTGRES_USER) \
            .option("password", POSTGRES_PASSWORD) \
            .option("driver", "org.postgresql.Driver") \
            .mode(modo) \
            .save()
        
        logger.info(f"Batch {batch_id} gravado com sucesso na tabela {tabela}")
    
    return df.writeStream \
        .foreachBatch(write_batch) \
        .outputMode("append") \
        .start()


def gravar_elasticsearch(df, indice):
    """Grava dados no Elasticsearch"""
    logger.info(f"Gravando dados no índice {indice} do Elasticsearch...")
    
    def write_to_es(batch_df, batch_id):
        batch_df.write \
            .format("org.elasticsearch.spark.sql") \
            .option("es.nodes", ELASTICSEARCH_HOST) \
            .option("es.port", ELASTICSEARCH_PORT) \
            .option("es.resource", indice) \
            .option("es.nodes.wan.only", "true") \
            .mode("append") \
            .save()
        
        logger.info(f"Batch {batch_id} gravado no Elasticsearch")
    
    return df.writeStream \
        .foreachBatch(write_to_es) \
        .outputMode("append") \
        .start()


def main():
    """Função principal do pipeline"""
    logger.info("Iniciando pipeline Spark Streaming...")
    
    # Criar sessão Spark
    spark = criar_spark_session()
    spark.sparkContext.setLogLevel("WARN")
    
    # Ler stream do Kafka
    df_kafka = ler_kafka_stream(spark)
    
    # Transformar dados
    df_transformed = transformar_dados(df_kafka)
    
    # Criar agregações
    df_agg = criar_agregacoes(df_transformed)
    
    # Gravar dados brutos no Postgres
    query_postgres_raw = gravar_postgres(
        df_transformed, 
        "eventos_raw"
    )
    
    # Gravar agregações no Postgres
    query_postgres_agg = gravar_postgres(
        df_agg, 
        "eventos_agregados"
    )
    
    # Gravar no Elasticsearch (opcional)
    query_elasticsearch = gravar_elasticsearch(
        df_transformed,
        "eventos"
    )
    
    logger.info("Pipeline iniciado! Aguardando dados do Kafka...")
    logger.info(f"Consumindo do tópico: {KAFKA_TOPIC}")
    
    # Aguardar término (Ctrl+C para parar)
    try:
        query_postgres_raw.awaitTermination()
    except KeyboardInterrupt:
        logger.info("Pipeline interrompido pelo usuário")
        spark.stop()


if __name__ == "__main__":
    main()
