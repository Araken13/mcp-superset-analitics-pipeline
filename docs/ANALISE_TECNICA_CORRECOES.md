# 🔬 Análise Técnica e Correções - SUPERSET

**Data:** 2025-12-05  
**Revisor:** Sistema de Análise Automatizada  
**Objetivo:** Identificar e corrigir problemas nos arquivos críticos

---

## 🚨 PROBLEMA #1: spark_supabase.py NÃO INICIA

### Análise Técnica

#### Erros Identificados

1. **Linha 113-116: Referência incorreta a `json_data`**

   ```python
   # ❌ ERRADO
   leads_df = batch_df.filter(col("data.tipo_evento") == "lead") \
                     .select(from_json(col("json_data"), leads_schema).alias("lead")) \
                     .select("lead.*") \
                     .drop("tipo_evento")
   ```

   **Problema:** `batch_df` não tem coluna `json_data`, pois já foi parseado na linha 93-98.  
   **Resultado:** Job falha silenciosamente ao tentar acessar coluna inexistente.

2. **Linha 100: Função `process_batch` recebe DataFrame errado**

   ```python
   # ❌ ERRADO
   query = df.select(col("json_data")) \  # df aqui é o DataFrame raw
       .writeStream \
       .foreachBatch(process_batch) \
   ```

   **Problema:** Está passando `df` (que tem `json_data`), mas `process_batch` espera um DataFrame já parseado.

3. **Linha 159: Passa DataFrame não parseado para foreachBatch**
   - `df` contém apenas `json_data` (string)
   - `process_batch` espera campos `data.tipo_evento`
   - Incompatibilidade causa falha silenciosa

---

### ✅ CORREÇÃO #1: spark_supabase_FIXED.py

```python
"""
Spark Job CORRIGIDO: Processa dados do Supabase e grava nas tabelas corretas
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
df_raw = df_kafka.select(col("value").cast("string").alias("json_data"))

# ✅ CORREÇÃO: Schema genérico para detectar tipo
detection_schema = StructType([
    StructField("tipo_evento", StringType(), True),
    StructField("id", StringType(), True)
])

def process_batch(batch_df, batch_id):
    """Processa cada batch e grava nas tabelas corretas"""
    logger.info(f"📦 Processando batch #{batch_id}")
    
    # Contar registros
    total_count = batch_df.count()
    if total_count == 0:
        logger.info("⏭️ Batch vazio, pulando...")
        return
    
    logger.info(f"📊 Total de registros no batch: {total_count}")
    
    # ✅ CORREÇÃO: Parse inicial para detectar tipo
    df_detected = batch_df.select(
        col("json_data"),
        from_json(col("json_data"), detection_schema).alias("detection")
    )
    
    # ✅ CORREÇÃO: Filtrar por tipo ANTES de fazer parse completo
    # Leads
    leads_raw = df_detected.filter(col("detection.tipo_evento") == "lead")
    if leads_raw.count() > 0:
        try:
            leads_df = leads_raw.select(
                from_json(col("json_data"), leads_schema).alias("lead")
            ).select("lead.*").drop("tipo_evento", "processado_em")
            
            leads_count = leads_df.count()
            logger.info(f"💾 Gravando {leads_count} leads no Postgres...")
            
            leads_df.write \
                .jdbc(url=POSTGRES_URL, 
                      table="leads", 
                      mode="append", 
                      properties=POSTGRES_PROPS)
            logger.info(f"✅ {leads_count} leads gravados com sucesso!")
        except Exception as e:
            logger.error(f"❌ Erro ao gravar leads: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Chat Sessions
    sessions_raw = df_detected.filter(col("detection.tipo_evento") == "chat_session")
    if sessions_raw.count() > 0:
        try:
            sessions_df = sessions_raw.select(
                from_json(col("json_data"), sessions_schema).alias("session")
            ).select("session.*").drop("tipo_evento", "processado_em")
            
            sessions_count = sessions_df.count()
            logger.info(f"💾 Gravando {sessions_count} sessões no Postgres...")
            
            sessions_df.write \
                .jdbc(url=POSTGRES_URL, 
                      table="chat_sessions", 
                      mode="append", 
                      properties=POSTGRES_PROPS)
            logger.info(f"✅ {sessions_count} sessões gravadas com sucesso!")
        except Exception as e:
            logger.error(f"❌ Erro ao gravar sessões: {str(e)}")
            import traceback
            traceback.print_exc()
    
    logger.info(f"✅ Batch #{batch_id} processado!")

# ✅ CORREÇÃO: Passar DataFrame RAW (com json_data)
query = df_raw \
    .writeStream \
    .foreachBatch(process_batch) \
    .outputMode("append") \
    .option("checkpointLocation", "/tmp/spark-checkpoint-supabase") \
    .start()

logger.info("✅ Stream iniciado! Aguardando dados...")

# Aguardar término
query.awaitTermination()
```

### Mudanças Principais

1. ✅ **Linha 120:** Adicionado schema de detecção (`detection_schema`)
2. ✅ **Linha 133:** Parse inicial apenas para detectar `tipo_evento`
3. ✅ **Linha 138:** Filtro aplicado ANTES de parse completo
4. ✅ **Linha 142:** Parse completo apenas nos registros filtrados
5. ✅ **Linha 182:** Passa `df_raw` para `process_batch`
6. ✅ **Linha 155, 169:** Adicionado tratamento de exceção com traceback

---

## 🔧 PROBLEMA #2: spark_app.py - Duplicação no Elasticsearch

### Análise Técnica

**Arquivo:** `spark_app.py` (linhas 180-195)

#### Problema

```python
# ❌ PROBLEMA: Sem controle de upsert no Elasticsearch
df_parsed.writeStream \
    .format("org.elasticsearch.spark.sql") \
    .outputMode("append") \
    .option("checkpointLocation", "/tmp/checkpoint-elasticsearch") \
    .option("es.resource", "eventos") \
    .start()
```

**Causa:** Cada insert cria um novo documento, gerando duplicatas quando o job é reiniciado.

### ✅ CORREÇÃO #2

```python
# ✅ SOLUÇÃO: Usar upsert por ID
df_parsed.writeStream \
    .format("org.elasticsearch.spark.sql") \
    .outputMode("append") \
    .option("checkpointLocation", "/tmp/checkpoint-elasticsearch") \
    .option("es.resource", "eventos") \
    .option("es.mapping.id", "id") \  # ← NOVO: Usar campo 'id' como chave
    .option("es.write.operation", "upsert") \  # ← NOVO: Fazer upsert
    .start()
```

**Benefícios:**

- ✅ Evita duplicatas
- ✅ Atualiza registros existentes
- ✅ Mantém apenas 1 documento por ID

---

## 🧹 PROBLEMA #3: Postgres - Duplicação por Chave Primária

### Análise

**Arquivo:** `spark_app.py` (linha ~135) e `spark_supabase.py` (linha 134)

#### Problema Atual

```python
# ❌ PROBLEMA: Duplicatas causam erro silencioso
leads_df.write \
    .jdbc(url=POSTGRES_URL, 
          table="leads", 
          mode="append",  # ← PROBLEMA: Sempre tenta INSERT
          properties=POSTGRES_PROPS)
```

**Resultado:** Como a tabela `leads` tem `id` como PRIMARY KEY, inserções duplicadas falham silenciosamente.

### ✅ CORREÇÃO #3

**Opção A: Usar UPSERT (PostgreSQL nativo)**

```python
# Requer função customizada
def upsert_to_postgres(batch_df, table_name):
    """Faz UPSERT no Postgres usando ON CONFLICT"""
    batch_df.foreachPartition(lambda partition: upsert_partition(partition, table_name))

def upsert_partition(partition, table_name):
    import psycopg2
    conn = psycopg2.connect(
        host="postgres", 
        port=5432, 
        dbname="superset", 
        user="superset", 
        password="superset"
    )
    cursor = conn.cursor()
    
    for row in partition:
        # Construir query ON CONFLICT DO UPDATE
        columns = row.asDict().keys()
        values = [row[col] for col in columns]
        
        placeholders = ", ".join(["%s"] * len(values))
        update_clause = ", ".join([f"{col} = EXCLUDED.{col}" for col in columns if col != 'id'])
        
        query = f"""
            INSERT INTO {table_name} ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT (id) DO UPDATE SET {update_clause}
        """
        cursor.execute(query, values)
    
    conn.commit()
    cursor.close()
    conn.close()
```

**Opção B: Filtrar duplicatas antes de inserir (mais simples)**

```python
# ✅ SOLUÇÃO SIMPLES: Verificar antes de inserir
from pyspark.sql import DataFrame

def insert_if_not_exists(df: DataFrame, table: str, id_column: str = "id"):
    """Insere apenas IDs que não existem"""
    # Ler IDs existentes
    existing_ids = spark.read \
        .jdbc(url=POSTGRES_URL, table=table, properties=POSTGRES_PROPS) \
        .select(id_column) \
        .distinct()
    
    # Filtrar apenas novos IDs
    new_records = df.join(existing_ids, on=id_column, how="left_anti")
    
    # Inserir apenas novos
    if new_records.count() > 0:
        new_records.write \
            .jdbc(url=POSTGRES_URL, table=table, mode="append", properties=POSTGRES_PROPS)
        return new_records.count()
    return 0
```

**Recomendação:** Usar Opção B (mais simples e seguro).

---

## 🗂️ PROBLEMA #4: Checkpoints Antigos

### Análise

**Problema:** Checkpoints do Spark acumulam e causam:

- Estado inconsistente ao reiniciar jobs
- Processamento duplicado ou perdido
- Consumo de disco

### ✅ CORREÇÃO #4: Script de Limpeza Automática

```bash
#!/bin/bash
# cleanup_spark_checkpoints.sh

echo "🧹 Limpando checkpoints antigos do Spark..."

# Checkpoints com mais de 7 dias
find /tmp -name "spark-checkpoint-*" -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null
find /tmp -name "checkpoint-*" -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null

echo "✅ Limpeza concluída!"
```

**Uso:**

```bash
# Executar semanalmente via cron
0 2 * * 0 /home/renan3/SUPERSET/cleanup_spark_checkpoints.sh
```

**Ou adicionar no docker-compose.yml:**

```yaml
spark-master:
  volumes:
    - ./cleanup_spark_checkpoints.sh:/scripts/cleanup.sh:ro
  command: >
    sh -c "
      (while true; do sleep 604800; /scripts/cleanup.sh; done) &
      /opt/spark/bin/spark-class org.apache.spark.deploy.master.Master
    "
```

---

## 🧪 PROBLEMA #5: Testes Incompletos

### Análise

**Arquivo:** `test_mcp.py`

#### Problemas

- Não testa integração Supabase
- Não valida dados no Elasticsearch
- Não testa recuperação de falhas

### ✅ CORREÇÃO #5: Testes Ampliados

```python
# test_mcp_extended.py

import pytest
import time
from superset_mcp import *
from supabase_to_kafka import *

class TestSupabaseIntegration:
    """Testes da integração Supabase"""
    
    def test_supabase_connection(self):
        """Testa conexão com Supabase"""
        stats = get_supabase_stats()
        assert "total_leads" in stats
        assert stats["total_leads"] >= 0
    
    def test_sync_leads(self):
        """Testa sincronização de leads"""
        result = sync_leads_to_kafka(limit=1, hours_ago=720)
        assert result["status"] == "success"
        assert "total_processed" in result
    
    def test_end_to_end_flow(self):
        """Testa fluxo completo: Inject → Kafka → Spark → Postgres"""
        # 1. Injetar evento
        event_id = inject_event("test_e2e", 999.99, "test_user")
        
        # 2. Aguardar processamento
        time.sleep(20)
        
        # 3. Verificar no Postgres
        import psycopg2
        conn = psycopg2.connect(
            host="localhost", port=5432,
            dbname="superset", user="superset", password="superset"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM eventos_raw WHERE usuario='test_user' ORDER BY processado_em DESC LIMIT 1")
        result = cursor.fetchone()
        
        assert result is not None
        assert result[1] == "test_user"  # usuario
        cursor.close()
        conn.close()
    
    def test_elasticsearch_indexing(self):
        """Testa se eventos aparecem no Elasticsearch"""
        import requests
        response = requests.get("http://localhost:9200/eventos/_count")
        data = response.json()
        assert data["count"] > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Executar:**

```bash
pip install pytest
pytest test_mcp_extended.py -v
```

---

## 📊 Resumo das Correções

| Problema | Arquivo | Correção | Prioridade | Esforço |
|----------|---------|----------|------------|---------|
| Job não inicia | spark_supabase.py | Corrigir parse de JSON | 🔴 ALTA | 2h |
| Duplicação Elasticsearch | spark_app.py | Adicionar upsert | 🟡 MÉDIA | 30min |
| Duplicação Postgres | Ambos | Filtrar IDs existentes | 🟡 MÉDIA | 1h |
| Checkpoints antigos | Sistema | Script de limpeza | 🟢 BAIXA | 30min |
| Testes incompletos | test_mcp.py | Adicionar testes E2E | 🟢 BAIXA | 2h |

**Tempo Total Estimado:** ~6 horas

---

## 🚀 Plano de Implementação

### Fase 1: Crítico (Hoje)

1. ✅ Criar `spark_supabase_FIXED.py`
2. ✅ Testar localmente
3. ✅ Deploy e validação

### Fase 2: Importante (Esta Semana)

4. ✅ Adicionar upsert no Elasticsearch
5. ✅ Implementar filtro de duplicatas no Postgres
6. ✅ Criar script de limpeza de checkpoints

### Fase 3: Melhorias (Próxima Semana)

7. ✅ Adicionar testes end-to-end
8. ✅ Implementar CI/CD
9. ✅ Documentar troubleshooting

---

**Próxima Ação Recomendada:**  
Implementar `spark_supabase_FIXED.py` e testar imediatamente.
