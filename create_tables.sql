-- Tabela para eventos brutos
CREATE TABLE IF NOT EXISTS eventos_raw (
    id VARCHAR(255),
    usuario VARCHAR(255),
    evento VARCHAR(255),
    valor DOUBLE PRECISION,
    timestamp TIMESTAMP,
    categoria VARCHAR(255),
    processado_em TIMESTAMP,
    PRIMARY KEY (id, timestamp)
);

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_eventos_raw_timestamp ON eventos_raw(timestamp);
CREATE INDEX IF NOT EXISTS idx_eventos_raw_categoria ON eventos_raw(categoria);
CREATE INDEX IF NOT EXISTS idx_eventos_raw_evento ON eventos_raw(evento);

-- Tabela para dados agregados
CREATE TABLE IF NOT EXISTS eventos_agregados (
    janela_inicio TIMESTAMP,
    janela_fim TIMESTAMP,
    categoria VARCHAR(255),
    evento VARCHAR(255),
    total_eventos BIGINT,
    valor_medio DOUBLE PRECISION,
    valor_total DOUBLE PRECISION,
    processado_em TIMESTAMP,
    PRIMARY KEY (janela_inicio, categoria, evento)
);

-- Índices para agregações
CREATE INDEX IF NOT EXISTS idx_eventos_agg_janela ON eventos_agregados(janela_inicio, janela_fim);
CREATE INDEX IF NOT EXISTS idx_eventos_agg_categoria ON eventos_agregados(categoria);

-- Views úteis para o Superset
CREATE OR REPLACE VIEW vw_eventos_ultimas_24h AS
SELECT 
    categoria,
    evento,
    COUNT(*) as total_eventos,
    AVG(valor) as valor_medio,
    SUM(valor) as valor_total,
    MIN(timestamp) as primeira_ocorrencia,
    MAX(timestamp) as ultima_ocorrencia
FROM eventos_raw
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY categoria, evento
ORDER BY total_eventos DESC;

CREATE OR REPLACE VIEW vw_eventos_por_hora AS
SELECT 
    DATE_TRUNC('hour', timestamp) as hora,
    categoria,
    COUNT(*) as total_eventos,
    AVG(valor) as valor_medio
FROM eventos_raw
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', timestamp), categoria
ORDER BY hora DESC;

-- Comentários nas tabelas
COMMENT ON TABLE eventos_raw IS 'Eventos brutos consumidos do Kafka';
COMMENT ON TABLE eventos_agregados IS 'Agregações calculadas por janela de tempo';
COMMENT ON VIEW vw_eventos_ultimas_24h IS 'Resumo dos eventos das últimas 24 horas';
COMMENT ON VIEW vw_eventos_por_hora IS 'Eventos agregados por hora dos últimos 7 dias';
