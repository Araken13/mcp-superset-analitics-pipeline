#!/bin/bash
echo "🛑 Parando containers antigos..."
docker rm -f $(docker ps -aq) || true

echo "🚀 Subindo pipeline SUPERSET..."
cd /home/renan3/SUPERSET
docker compose up -d

echo "⏳ Aguardando serviços subirem (30s)..."
sleep 30

echo "📋 Criando tabelas no Postgres..."
./init_database.sh

echo "🔥 Submetendo Spark Job..."
docker cp spark_app.py spark-master:/opt/spark-apps/spark_app.py
docker exec -d spark-master bin/spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.7.0,org.elasticsearch:elasticsearch-spark-30_2.12:8.11.0 \
  /opt/spark-apps/spark_app.py

echo "✅ Ambiente pronto!"
