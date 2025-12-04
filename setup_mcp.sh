#!/bin/bash

# 🚀 Script de Setup Automatizado - SUPERSET MCP
# Este script configura todo o ambiente necessário para rodar o servidor MCP

set -e  # Parar em caso de erro

echo "════════════════════════════════════════════════════════════"
echo "  🚀 SUPERSET MCP - Setup Automatizado"
echo "════════════════════════════════════════════════════════════"
echo ""

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Função para printar com cor
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "ℹ️  $1"
}

# 1. Verificar pré-requisitos
echo "📋 Verificando pré-requisitos..."
echo ""

# Verificar Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python encontrado: $PYTHON_VERSION"
else
    print_error "Python 3 não encontrado. Instale com: sudo apt install python3 python3-venv python3-full"
    exit 1
fi

# Verificar Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
    print_success "Docker encontrado: $DOCKER_VERSION"
else
    print_error "Docker não encontrado. Instale Docker Desktop ou Docker Engine."
    exit 1
fi

# Verificar Docker Compose
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    print_success "Docker Compose encontrado"
else
    print_error "Docker Compose não encontrado."
    exit 1
fi

echo ""

# 2. Criar e ativar ambiente virtual
echo "🐍 Configurando ambiente virtual Python..."
echo ""

if [ ! -d "venv" ]; then
    print_info "Criando venv..."
    python3 -m venv venv
    print_success "Ambiente virtual criado"
else
    print_warning "Ambiente virtual já existe (pulando criação)"
fi

# Ativar venv
source venv/bin/activate
print_success "Ambiente virtual ativado"

echo ""

# 3. Instalar dependências Python
echo "📦 Instalando dependências Python..."
echo ""

pip install --upgrade pip > /dev/null 2>&1
print_success "pip atualizado"

print_info "Instalando pacotes (isso pode demorar alguns minutos)..."
pip install -r requirements.txt
print_success "Dependências instaladas"

echo ""

# 4. Verificar/Iniciar Docker Containers
echo "🐳 Configurando containers Docker..."
echo ""

# Verificar se containers já estão rodando
RUNNING_CONTAINERS=$(docker ps --filter "name=superset\|kafka\|spark\|postgres\|elasticsearch" --format "{{.Names}}" | wc -l)

if [ "$RUNNING_CONTAINERS" -gt 0 ]; then
    print_warning "Containers já estão rodando ($RUNNING_CONTAINERS encontrados)"
    read -p "Deseja reiniciar? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Parando containers existentes..."
        docker-compose down
    else
        print_info "Mantendo containers atuais"
    fi
fi

# Subir containers
if [ "$RUNNING_CONTAINERS" -eq 0 ] || [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Iniciando containers (isso pode demorar 1-2 minutos)..."
    
    # Tentar com buildx, se falhar usar método tradicional
    if docker-compose up -d --build 2>&1 | grep -q "buildx"; then
        print_warning "buildx não disponível, usando build tradicional..."
        DOCKER_BUILDKIT=0 docker-compose up -d --build
    fi
    
    print_success "Containers iniciados"
    
    # Aguardar serviços ficarem prontos
    print_info "Aguardando serviços ficarem prontos (30s)..."
    sleep 30
fi

echo ""

# 5. Inicializar banco de dados
echo "🗄️  Inicializando banco de dados..."
echo ""

if [ -f "init_database.sh" ]; then
    chmod +x init_database.sh
    ./init_database.sh
    print_success "Banco de dados inicializado"
else
    print_warning "Script init_database.sh não encontrado (pulando)"
fi

echo ""

# 6. Verificar status final
echo "🔍 Verificando status dos serviços..."
echo ""

# Função para verificar porta
check_port() {
    local port=$1
    local service=$2
    if nc -z localhost $port 2>/dev/null; then
        print_success "$service (porta $port)"
    else
        print_warning "$service (porta $port) - não acessível"
    fi
}

check_port 8080 "Spark Master"
check_port 5432 "Postgres"
check_port 29092 "Kafka"
check_port 9200 "Elasticsearch"

echo ""

# 7. Teste rápido do MCP
echo "🧪 Testando servidor MCP..."
echo ""

if [ -f "test_mcp.py" ]; then
    print_info "Executando testes..."
    python test_mcp.py > /tmp/mcp_test_output.txt 2>&1
    
    # Verificar se teve sucesso
    if grep -q "TESTES CONCLUÍDOS" /tmp/mcp_test_output.txt; then
        print_success "Testes do MCP passaram!"
        
        # Mostrar resumo
        echo ""
        echo "📊 Resumo dos testes:"
        grep -E "🟢|✅|⚡" /tmp/mcp_test_output.txt | head -n 10
    else
        print_warning "Alguns testes falharam. Veja detalhes em /tmp/mcp_test_output.txt"
    fi
else
    print_warning "Arquivo test_mcp.py não encontrado (pulando testes)"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✨ Setup Concluído!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📚 Próximos passos:"
echo ""
echo "1. Ativar o ambiente virtual:"
echo "   source venv/bin/activate"
echo ""
echo "2. Testar o MCP:"
echo "   python test_mcp.py"
echo ""
echo "3. Iniciar o servidor MCP:"
echo "   mcp run superset_mcp.py"
echo ""
echo "4. Acessar interfaces web:"
echo "   - Spark Master: http://localhost:8080"
echo "   - Superset: http://localhost:8088 (admin/admin)"
echo "   - Kibana: http://localhost:5601"
echo ""
echo "📖 Documentação completa: MCP_DOCUMENTATION.md"
echo ""
