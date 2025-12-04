#!/bin/bash

echo "🚀 Executando aplicação Spark..."

# Copiar o script Python para o container
echo "📋 Copiando spark_app.py para o container..."
docker cp spark_app.py spark-master:/opt/spark-apps/

# Executar o spark-submit
echo "▶️  Iniciando Spark Streaming..."
docker exec spark-master spark-submit \
    --master spark://spark-master:7077 \
    --deploy-mode client \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.7.0,org.elasticsearch:elasticsearch-spark-30_2.12:8.11.0 \
    --conf spark.executor.memory=1g \
    --conf spark.executor.cores=1 \
    --conf spark.driver.memory=1g \
    --conf spark.sql.shuffle.partitions=2 \
    /opt/spark-apps/spark_app.py

echo "✅ Aplicação Spark finalizada!"
