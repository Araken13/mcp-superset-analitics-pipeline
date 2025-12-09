#!/bin/bash
###############################################################################
# SPARK JOB WATCHDOG - Monitora e Reinicia Automaticamente
# Autor: Sistema Automatizado
# Data: 2025-12-05
# Descrição: Garante que o Spark job está SEMPRE rodando
###############################################################################

set -e

# Configurações
CHECK_INTERVAL=60  # Verificar a cada 60 segundos
MAX_RETRIES=3      # Máximo de tentativas de restart consecutivas
RETRY_DELAY=30     # Delay entre tentativas (segundos)
LOG_FILE="/tmp/spark-watchdog.log"

# Contadores
CONSECUTIVE_FAILURES=0

# Cores para log
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

check_spark_job() {
    # Verifica se o Spark job está rodando
    
    # Método 1: Verificar via API do Spark Master
    APPS_RUNNING=$(docker exec spark-master curl -s http://localhost:8080/json/ 2>/dev/null | \
                   python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('activeapps', [])))" 2>/dev/null || echo "0")
    
    if [ "$APPS_RUNNING" -ge 1 ]; then
        return 0  # Job está rodando
    fi
    
    # Método 2: Verificar processo spark-submit
    if docker exec spark-master pgrep -f "spark-submit.*spark_app.py" > /dev/null 2>&1; then
        return 0  # Processo existe
    fi
    
    return 1  # Job NÃO está rodando
}

start_spark_job() {
    # Inicia o Spark job
    
    log_info "🚀 Iniciando Spark job..."
    
    # Matar jobs antigos (se existirem)
    docker exec spark-master pkill -9 -f "spark-submit.*spark_app.py" 2>/dev/null || true
    sleep 3
    
    # Limpar checkpoints se houver muitos restarts
    if [ $CONSECUTIVE_FAILURES -ge 2 ]; then
        log_warning "Múltiplas falhas detectadas. Limpando checkpoints..."
        docker exec spark-master rm -rf /tmp/spark-checkpoint-* 2>/dev/null || true
        docker exec spark-master rm -rf /tmp/checkpoint-* 2>/dev/null || true
    fi
    
    # Iniciar job em background
    docker exec -d spark-master bin/spark-submit \
        --master spark://spark-master:7077 \
        --deploy-mode client \
        --driver-memory 1g \
        --executor-memory 1g \
        --total-executor-cores 2 \
        --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.7.0,org.elasticsearch:elasticsearch-spark-30_2.12:8.11.0 \
        --conf spark.streaming.stopGracefullyOnShutdown=true \
        --conf spark.sql.streaming.checkpointLocation=/tmp/spark-checkpoint-eventos \
        /opt/spark-apps/spark_app.py > /dev/null 2>&1
    
    # Aguardar inicialização
    log_info "⏳ Aguardando job inicializar (30s)..."
    sleep 30
    
    # Verificar se iniciou com sucesso
    if check_spark_job; then
        log_info "✅ Spark job iniciado com sucesso!"
        CONSECUTIVE_FAILURES=0
        return 0
    else
        log_error "❌ Falha ao iniciar Spark job"
        CONSECUTIVE_FAILURES=$((CONSECUTIVE_FAILURES + 1))
        return 1
    fi
}

restart_spark_job() {
    # Reinicia o Spark job com retry logic
    
    log_warning "🔄 Reiniciando Spark job (tentativa $CONSECUTIVE_FAILURES/$MAX_RETRIES)..."
    
    if [ $CONSECUTIVE_FAILURES -ge $MAX_RETRIES ]; then
        log_error "⚠️ ALERTA CRÍTICO: Máximo de tentativas atingido!"
        log_error "⚠️ Aguardando $((RETRY_DELAY * 2)) segundos antes de tentar novamente..."
        sleep $((RETRY_DELAY * 2))
        CONSECUTIVE_FAILURES=0  # Reset contador
    fi
    
    if start_spark_job; then
        log_info "✅ Spark job restaurado com sucesso"
        return 0
    else
        log_error "❌ Falha ao restaurar Spark job"
        sleep $RETRY_DELAY
        return 1
    fi
}

verify_dependencies() {
    # Verifica se dependências estão OK
    
    # Verificar se Spark Master está rodando
    if ! docker exec spark-master curl -s http://localhost:8080 > /dev/null 2>&1; then
        log_error "❌ Spark Master não está acessível!"
        return 1
    fi
    
    # Verificar se Kafka está rodando
    if ! docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list > /dev/null 2>&1; then
        log_warning "⚠️ Kafka não está acessível!"
        return 1
    fi
    
    # Verificar se Postgres está rodando
    if ! docker exec postgres pg_isready -U superset > /dev/null 2>&1; then
        log_warning "⚠️ Postgres não está acessível!"
        return 1
    fi
    
    return 0
}

main_loop() {
    # Loop principal de monitoramento
    
    log_info "🔍 Watchdog iniciado. Verificando a cada ${CHECK_INTERVAL}s..."
    log_info "📝 Logs salvos em: $LOG_FILE"
    
    # Garantir que job está rodando no início
    if ! check_spark_job; then
        log_warning "⚠️ Spark job não está rodando. Iniciando..."
        start_spark_job
    else
        log_info "✅ Spark job já está rodando"
    fi
    
    # Loop infinito de monitoramento
    while true; do
        sleep $CHECK_INTERVAL
        
        # Verificar dependências primeiro
        if ! verify_dependencies; then
            log_warning "⚠️ Dependências não estão OK. Aguardando próximo ciclo..."
            continue
        fi
        
        # Verificar se job está rodando
        if check_spark_job; then
            # Job OK - Reset contador
            if [ $CONSECUTIVE_FAILURES -gt 0 ]; then
                log_info "✅ Spark job recuperado. Reset contador de falhas."
                CONSECUTIVE_FAILURES=0
            fi
        else
            # Job FALHOU - Tentar reiniciar
            log_error "❌ Spark job não está rodando!"
            restart_spark_job
        fi
    done
}

# Tratamento de sinais
trap 'log_info "🛑 Watchdog interrompido"; exit 0' SIGINT SIGTERM

# Iniciar watchdog
log_info "╔══════════════════════════════════════════════════════════╗"
log_info "║          SPARK JOB WATCHDOG - INICIANDO                 ║"
log_info "╚══════════════════════════════════════════════════════════╝"

main_loop
