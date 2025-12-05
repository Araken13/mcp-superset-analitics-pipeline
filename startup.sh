#!/bin/bash
###############################################################################
# SUPERSET Pipeline - Script de Inicialização Automática
# Autor: Sistema Automatizado
# Data: 2025-12-05
# Descrição: Inicializa todo o pipeline automaticamente
###############################################################################

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Diretório do projeto
PROJECT_DIR="/home/renan3/SUPERSET"
cd "$PROJECT_DIR"

# Arquivo de log
LOG_FILE="/tmp/superset-startup.log"
echo "=== SUPERSET Pipeline Startup - $(date) ===" > "$LOG_FILE"

# Funções de logging
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

###############################################################################
# 1. VERIFICAR PRÉ-REQUISITOS
###############################################################################

log_info "🔍 Verificando pré-requisitos..."

# Verificar se Docker está rodando
if ! docker ps &> /dev/null; then
    log_error "Docker não está rodando!"
    log_info "Tentando iniciar Docker..."
    sudo service docker start
    sleep 5
    
    if ! docker ps &> /dev/null; then
        log_error "Falha ao iniciar Docker. Abortando."
        exit 1
    fi
fi

log_success "Docker está rodando"

# Verificar se docker-compose existe
if ! command -v docker &> /dev/null; then
    log_error "docker-compose não encontrado!"
    exit 1
fi

log_success "docker-compose encontrado"

###############################################################################
# 2. PARAR CONTAINERS ANTIGOS (se existirem)
###############################################################################

log_info "🛑 Parando containers antigos..."
docker compose down &>> "$LOG_FILE" || true
log_success "Containers antigos parados"

###############################################################################
# 3. LIMPAR RECURSOS (opcional)
###############################################################################

log_info "🧹 Limpando recursos antigos..."

# Limpar checkpoints antigos (mais de 7 dias)
find /tmp -name "spark-checkpoint-*" -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null || true
find /tmp -name "checkpoint-*" -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null || true

log_success "Recursos limpos"

###############################################################################
# 4. INICIAR CONTAINERS
###############################################################################

log_info "🚀 Iniciando containers Docker..."
docker compose up -d >> "$LOG_FILE" 2>&1

if [ $? -ne 0 ]; then
    log_error "Falha ao iniciar containers!"
    exit 1
fi

log_success "Containers iniciados"

###############################################################################
# 5. AGUARDAR CONTAINERS FICAREM HEALTHY
###############################################################################

log_info "⏳ Aguardando containers ficarem saudáveis (max 2 minutos)..."

TIMEOUT=120
ELAPSED=0
INTERVAL=5

while [ $ELAPSED -lt $TIMEOUT ]; do
    HEALTHY_COUNT=$(docker ps --format "{{.Status}}" | grep -c "healthy" || true)
    TOTAL_COUNT=$(docker ps --format "{{.Names}}" | wc -l)
    
    log_info "Containers healthy: $HEALTHY_COUNT/$TOTAL_COUNT"
    
    # Consideramos OK se pelo menos 7 serviços estão healthy
    if [ $HEALTHY_COUNT -ge 7 ]; then
        log_success "Containers estão saudáveis!"
        break
    fi
    
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    log_warning "Timeout aguardando containers. Continuando mesmo assim..."
fi

# Aguardar mais 10s para garantir
log_info "Aguardando estabilização (10s)..."
sleep 10

###############################################################################
# 6. COPIAR SPARK JOBS PARA O CONTAINER
###############################################################################

log_info "📦 Copiando Spark jobs para o container..."

# Copiar spark_app.py (principal)
docker cp spark_app.py spark-master:/opt/spark-apps/ >> "$LOG_FILE" 2>&1
log_success "spark_app.py copiado"

# Copiar spark_supabase_FIXED.py
if [ -f "spark_supabase_FIXED.py" ]; then
    docker cp spark_supabase_FIXED.py spark-master:/opt/spark-apps/ >> "$LOG_FILE" 2>&1
    log_success "spark_supabase_FIXED.py copiado"
fi

###############################################################################
# 7. MATAR JOBS SPARK ANTIGOS
###############################################################################

log_info "🔪 Matando jobs Spark antigos..."
docker exec spark-master pkill -f spark-submit &>> "$LOG_FILE" || true
sleep 3
log_success "Jobs antigos removidos"

###############################################################################
# 8. INICIAR SPARK JOB PRINCIPAL (spark_app.py)
###############################################################################

log_info "⚡ Iniciando Spark Job principal (spark_app.py)..."

docker exec -d spark-master bin/spark-submit \
    --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.7.0,org.elasticsearch:elasticsearch-spark-30_2.12:8.11.0 \
    /opt/spark-apps/spark_app.py >> "$LOG_FILE" 2>&1

if [ $? -ne 0 ]; then
    log_error "Falha ao iniciar Spark Job principal!"
else
    log_success "Spark Job principal iniciado"
fi

# Aguardar job inicializar
sleep 15

###############################################################################
# 9. VERIFICAR SE SPARK JOB ESTÁ RODANDO
###############################################################################

log_info "🔍 Verificando se Spark Job está ativo..."

APPS_RUNNING=$(docker exec spark-master curl -s http://localhost:8080/json/ 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('activeapps', [])))" 2>/dev/null || echo "0")

if [ "$APPS_RUNNING" -ge 1 ]; then
    log_success "Spark Job está rodando ($APPS_RUNNING app(s) ativa(s))"
else
    log_warning "Spark Job pode não estar rodando. Verificar logs manualmente."
fi

###############################################################################
# 10. VERIFICAR CONECTIVIDADE DOS SERVIÇOS
###############################################################################

log_info "🔌 Verificando conectividade dos serviços..."

# Verificar Kafka
if docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list &>> "$LOG_FILE"; then
    log_success "Kafka está acessível"
else
    log_warning "Kafka pode não estar acessível"
fi

# Verificar Postgres
if docker exec postgres pg_isready -U superset &>> "$LOG_FILE"; then
    log_success "PostgreSQL está acessível"
else
    log_warning "PostgreSQL pode não estar acessível"
fi

# Verificar Elasticsearch
if curl -s http://localhost:9200/_cluster/health &>> "$LOG_FILE"; then
    log_success "Elasticsearch está acessível"
else
    log_warning "Elasticsearch pode não estar acessível"
fi

###############################################################################
# 11. RESUMO FINAL
###############################################################################

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║          SUPERSET PIPELINE - INICIALIZAÇÃO COMPLETA          ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Status dos containers
log_info "📊 Status dos Containers:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "NAME|superset|postgres|kafka|spark|elasticsearch|kibana|zookeeper|pgadmin"

echo ""
log_info "🌐 URLs de Acesso:"
echo "  • Superset:      http://localhost:8088"
echo "  • Kibana:        http://localhost:5601"
echo "  • Spark Master:  http://localhost:8080"
echo "  • Elasticsearch: http://localhost:9200"
echo "  • pgAdmin:       http://localhost:5050"

echo ""
log_info "📝 Logs disponíveis em: $LOG_FILE"

echo ""
log_success "✅ Pipeline inicializado e pronto para uso!"
echo ""

exit 0
