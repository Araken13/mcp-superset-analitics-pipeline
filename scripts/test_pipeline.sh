#!/bin/bash

echo "🧪 Testando Pipeline End-to-End"
echo "================================"
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para verificar serviço
check_service() {
    local service=$1
    local url=$2
    
    echo -n "Verificando $service... "
    if curl -f -s "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ OK${NC}"
        return 0
    else
        echo -e "${RED}❌ FALHOU${NC}"
        return 1
    fi
}

echo "1️⃣  Verificando serviços..."
echo "----------------------------"
check_service "Kafka" "http://localhost:9092"
check_service "Postgres" "http://localhost:5432"
check_service "Elasticsearch" "http://localhost:9200"
check_service "Spark Master" "http://localhost:8080"
check_service "Superset" "http://localhost:8088"
check_service "Kibana" "http://localhost:5601"
echo ""

echo "2️⃣  Criando tópico Kafka..."
echo "----------------------------"
docker exec kafka kafka-topics --create \
    --topic eventos \
    --bootstrap-server localhost:9092 \
    --partitions 3 \
    --replication-factor 1 \
    --if-not-exists

docker exec kafka kafka-topics --list --bootstrap-server localhost:9092
echo ""

echo "3️⃣  Verificando tabelas no Postgres..."
echo "---------------------------------------"
docker exec postgres psql -U superset -d superset -c "\dt"
echo ""

echo "4️⃣  Testando produção de mensagens no Kafka..."
echo "-----------------------------------------------"
echo "Enviando 5 mensagens de teste..."
for i in {1..5}; do
    MESSAGE=$(cat <<EOF
{
  "id": "test-$i",
  "usuario": "usuario_teste",
  "evento": "teste_pipeline",
  "valor": $((RANDOM % 1000 + 1)),
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%S")",
  "categoria": "teste"
}
EOF
)
    echo "$MESSAGE" | docker exec -i kafka kafka-console-producer \
        --topic eventos \
        --bootstrap-server localhost:9092
    echo "✅ Mensagem $i enviada"
    sleep 1
done
echo ""

echo "5️⃣  Verificando mensagens no Kafka..."
echo "--------------------------------------"
echo "Lendo últimas 5 mensagens do tópico..."
timeout 5 docker exec kafka kafka-console-consumer \
    --topic eventos \
    --bootstrap-server localhost:9092 \
    --from-beginning \
    --max-messages 5 2>/dev/null
echo ""

echo "6️⃣  Aguardando processamento do Spark..."
echo "-----------------------------------------"
echo "⏳ Aguardando 10 segundos..."
sleep 10
echo ""

echo "7️⃣  Verificando dados no Postgres..."
echo "-------------------------------------"
echo "Eventos brutos:"
docker exec postgres psql -U superset -d superset -c \
    "SELECT COUNT(*) as total_eventos FROM eventos_raw;"
echo ""
echo "Eventos agregados:"
docker exec postgres psql -U superset -d superset -c \
    "SELECT COUNT(*) as total_agregacoes FROM eventos_agregados;"
echo ""

echo "8️⃣  Verificando índice no Elasticsearch..."
echo "-------------------------------------------"
curl -s "http://localhost:9200/eventos/_count" | jq '.'
echo ""

echo "✅ Teste completo!"
echo ""
echo "📊 Próximos passos:"
echo "   1. Acesse o Superset: http://localhost:8088 (admin/admin)"
echo "   2. Acesse o Kibana: http://localhost:5601"
echo "   3. Execute o produtor: python3 kafka_producer.py"
echo "   4. Execute o Spark: ./run_spark.sh"
echo ""
