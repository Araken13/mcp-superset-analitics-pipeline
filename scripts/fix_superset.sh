#!/bin/bash

echo "🔧 Corrigindo conexão do Superset com Postgres..."

# 1. Parar containers
echo "⏹️  Parando containers..."
docker compose down

# 2. Remover volume do Superset (força uso do Postgres)
echo "🗑️  Removendo volume antigo do Superset..."
docker volume rm superset_superset_home 2>/dev/null || true

# 3. Subir novamente
echo "🚀 Subindo containers..."
docker compose up -d

# 4. Aguardar Postgres ficar pronto
echo "⏳ Aguardando Postgres..."
until docker exec postgres pg_isready -U superset > /dev/null 2>&1; do
    sleep 2
done
echo "✅ Postgres está pronto!"

# 5. Aguardar Superset inicializar (60 segundos)
echo "⏳ Aguardando Superset inicializar (60s)..."
sleep 60

# 6. Verificar logs
echo "📋 Verificando logs do Superset..."
docker compose logs superset --tail=20

echo ""
echo "✅ Correção aplicada!"
echo ""
echo "🌐 Acesse: http://localhost:8088"
echo "👤 Usuário: admin"
echo "🔑 Senha: admin"
echo ""
echo "Para adicionar database no Superset, use:"
echo "postgresql://superset:superset@postgres:5432/superset"
echo ""
