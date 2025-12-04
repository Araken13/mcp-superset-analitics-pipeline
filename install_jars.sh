#!/bin/bash

echo "📦 Instalando dependências Kafka para Spark..."

docker exec -it spark-master bash -c '
  cd /opt/spark/jars

  echo "🔹 Baixando spark-sql-kafka..."
  wget -q https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.1.2/spark-sql-kafka-0-10_2.12-3.1.2.jar

  echo "🔹 Baixando kafka-clients..."
  wget -q https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/2.8.0/kafka-clients-2.8.0.jar

  echo "🔹 Baixando spark-token-provider-kafka..."
  wget -q https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.1.2/spark-token-provider-kafka-0-10_2.12-3.1.2.jar

  echo "🔹 Baixando commons-pool2..."
  wget -q https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar

  echo "✅ JARs instalados com sucesso!"
  ls -lh | grep -E "kafka|pool"
'

