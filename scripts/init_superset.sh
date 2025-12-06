#!/bin/bash

echo "🚀 Inicializando Apache Superset..."

# Aguardar Postgres estar pronto
echo "⏳ Aguardando Postgres..."
until docker exec postgres pg_isready -U superset > /dev/null 2>&1; do
    sleep 2
done
echo "✅ Postgres está pronto!"

# Inicializar banco de dados do Superset
echo "📦 Inicializando banco de dados..."
docker exec superset superset db upgrade

# Criar usuário admin
echo "👤 Criando usuário admin..."
docker exec superset superset fab create-admin \
    --username admin \
    --firstname Admin \
    --lastname User \
    --email admin@superset.com \
    --password admin

# Inicializar Superset
echo "🔧 Inicializando Superset..."
docker exec superset superset init

# Carregar exemplos (opcional - remova se não quiser)
# echo "📊 Carregando exemplos..."
# docker exec superset superset load-examples

echo "✅ Superset inicializado com sucesso!"
echo ""
echo "🌐 Acesse: http://localhost:8088"
echo "👤 Usuário: admin"
echo "🔑 Senha: admin"
echo ""
