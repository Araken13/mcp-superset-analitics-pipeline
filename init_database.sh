#!/bin/bash

echo "🗄️  Criando tabelas no Postgres..."

# Aguardar Postgres estar pronto
echo "⏳ Aguardando Postgres..."
until docker exec postgres pg_isready -U superset > /dev/null 2>&1; do
    sleep 2
done

# Criar tabelas
echo "📋 Executando script SQL..."
docker exec -i postgres psql -U superset -d superset < create_tables.sql

echo "✅ Tabelas criadas com sucesso!"
echo ""
echo "📊 Tabelas disponíveis:"
echo "   - eventos_raw (dados brutos)"
echo "   - eventos_agregados (agregações)"
echo "   - vw_eventos_ultimas_24h (view)"
echo "   - vw_eventos_por_hora (view)"
echo ""
