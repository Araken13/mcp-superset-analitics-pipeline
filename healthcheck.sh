#!/bin/bash
###############################################################################
# SUPERSET Pipeline - Health Check Script
# Verifica saúde de todos os componentes do pipeline
###############################################################################

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║        SUPERSET PIPELINE - VERIFICAÇÃO DE SAÚDE              ║"
echo "║        $(date '+%Y-%m-%d %H:%M:%S')                                    ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

check() {
    local name="$1"
    local command="$2"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    printf "%-40s " "$name"
    
    if eval "$command" &> /dev/null; then
        echo -e "${GREEN}✅ OK${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}❌ FALHOU${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

echo "🐳 Verificando Containers Docker..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check "Docker está rodando" "docker ps"
check "Container: postgres" "docker ps | grep -q postgres"
check "Container: kafka" "docker ps | grep -q kafka"
check "Container: zookeeper" "docker ps | grep -q zookeeper"
check "Container: elasticsearch" "docker ps | grep -q elasticsearch"
check "Container: kibana" "docker ps | grep -q kibana"
check "Container: spark-master" "docker ps | grep -q spark-master"
check "Container: spark-worker-1" "docker ps | grep -q spark-worker-1"
check "Container: superset" "docker ps | grep -q superset"

echo ""
echo "🔌 Verificando Conectividade de Serviços..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

check "PostgreSQL respondendo" "docker exec postgres pg_isready -U superset"
check "Kafka respondendo" "docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list"
check "Elasticsearch respondendo" "curl -s http://localhost:9200/_cluster/health"
check "Kibana acessível" "curl -s http://localhost:5601/api/status"
check "Superset acessível" "curl -s http://localhost:8088/health"

echo ""
echo "⚡ Verificando Spark Jobs..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Verificar Spark Master UI
if curl -s http://localhost:8080 &> /dev/null; then
    APPS_ACTIVE=$(docker exec spark-master curl -s http://localhost:8080/json/ 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('activeapps', [])))" 2>/dev/null || echo "0")
    
    printf "%-40s " "Spark Master UI acessível"
    echo -e "${GREEN}✅ OK${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    printf "%-40s " "Spark Jobs ativos"
    if [ "$APPS_ACTIVE" -ge 1 ]; then
        echo -e "${GREEN}✅ OK ($APPS_ACTIVE app(s))${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo -e "${RED}❌ FALHOU (0 apps)${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
else
    printf "%-40s " "Spark Master UI"
    echo -e "${RED}❌ FALHOU${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
fi

echo ""
echo "💾 Verificando Dados..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Verificar tabelas Postgres
EVENTOS_COUNT=$(docker exec postgres psql -U superset -d superset -tAc "SELECT COUNT(*) FROM eventos_raw" 2>/dev/null || echo "0")
printf "%-40s " "Eventos no Postgres"
if [ "$EVENTOS_COUNT" != "0" ]; then
    echo -e "${GREEN}✅ OK ($EVENTOS_COUNT eventos)${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${YELLOW}⚠️  VAZIO${NC}"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

# Verificar índice Elasticsearch
ES_COUNT=$(curl -s "http://localhost:9200/eventos/_count" 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin).get('count', 0))" 2>/dev/null || echo "0")
printf "%-40s " "Eventos no Elasticsearch"
if [ "$ES_COUNT" != "0" ]; then
    echo -e "${GREEN}✅ OK ($ES_COUNT eventos)${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${YELLOW}⚠️  VAZIO${NC}"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                         RESUMO                                ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

PERCENTAGE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

echo "  Total de Verificações: $TOTAL_CHECKS"
echo -e "  ${GREEN}✅ Passaram: $PASSED_CHECKS${NC}"
echo -e "  ${RED}❌ Falharam: $FAILED_CHECKS${NC}"
echo "  📊 Taxa de Sucesso: $PERCENTAGE%"
echo ""

if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}${NC}🎉 SISTEMA TOTALMENTE OPERACIONAL! 🎉${GREEN}${NC}"
    echo ""
    exit 0
elif [ $PERCENTAGE -ge 80 ]; then
    echo -e "${YELLOW}⚠️  SISTEMA PARCIALMENTE OPERACIONAL${NC}"
    echo "   Alguns componentes precisam de atenção."
    echo ""
    exit 1
else
    echo -e "${RED}🚨 SISTEMA COM PROBLEMAS CRÍTICOS 🚨${NC}"
    echo "   Verificar logs e reiniciar se necessário."
    echo ""
    exit 2
fi
