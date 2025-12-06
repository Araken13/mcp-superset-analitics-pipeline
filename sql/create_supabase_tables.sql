-- ============================================
-- ESPELHAMENTO DAS TABELAS DO SUPABASE
-- Para garantir que não perdemos nenhum dado
-- ============================================

-- Extensão para UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TABELA: LEADS (espelho do Supabase)
-- ============================================
DROP TABLE IF EXISTS leads CASCADE;

CREATE TABLE leads (
    id UUID PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    telefone VARCHAR(20),
    nome_empresa VARCHAR(255),
    nome_projeto VARCHAR(255),
    localizacao JSONB DEFAULT '{}',
    interesse TEXT[],
    score_qualificacao INTEGER DEFAULT 0 CHECK (score_qualificacao >= 0 AND score_qualificacao <= 100),
    status_lead VARCHAR(50) DEFAULT 'novo' CHECK (status_lead IN ('novo', 'qualificado', 'em_contato', 'convertido', 'perdido')),
    origem VARCHAR(100) DEFAULT 'chatbot',
    utm_source VARCHAR(100),
    utm_medium VARCHAR(100),
    utm_campaign VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_interaction_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX idx_leads_email ON leads(email);
CREATE INDEX idx_leads_status ON leads(status_lead);
CREATE INDEX idx_leads_score ON leads(score_qualificacao DESC);
CREATE INDEX idx_leads_created_at ON leads(created_at DESC);
CREATE INDEX idx_leads_interesse ON leads USING GIN(interesse);

-- ============================================
-- TABELA: CHAT_SESSIONS (espelho do Supabase)
-- ============================================
DROP TABLE IF EXISTS chat_sessions CASCADE;

CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY,
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
    session_token VARCHAR(255),
    user_agent TEXT,
    ip_address INET,
    total_messages INTEGER DEFAULT 0,
    duration_seconds INTEGER DEFAULT 0,
    pages_visited TEXT[],
    perguntas_feitas TEXT[],
    intencao_detectada VARCHAR(100),
    nivel_interesse VARCHAR(50) DEFAULT 'baixo' CHECK (nivel_interesse IN ('baixo', 'medio', 'alto')),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    processado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_sessions_lead ON chat_sessions(lead_id);
CREATE INDEX idx_sessions_active ON chat_sessions(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_sessions_started ON chat_sessions(started_at DESC);

-- ============================================
-- VIEWS ÚTEIS
-- ============================================

-- View: Resumo de Leads
CREATE OR REPLACE VIEW v_leads_resumo AS
SELECT
    l.id,
    l.nome,
    l.email,
    l.telefone,
    l.nome_empresa,
    l.score_qualificacao,
    l.status_lead,
    l.interesse,
    COUNT(DISTINCT cs.id) as total_sessoes,
    l.created_at,
    l.last_interaction_at,
    EXTRACT(EPOCH FROM (NOW() - l.last_interaction_at))/86400 as dias_desde_ultima_interacao
FROM leads l
LEFT JOIN chat_sessions cs ON cs.lead_id = l.id
GROUP BY l.id;

-- View: Leads Qualificados (score >= 50)
CREATE OR REPLACE VIEW v_leads_qualificados AS
SELECT *
FROM leads
WHERE score_qualificacao >= 50
ORDER BY score_qualificacao DESC, last_interaction_at DESC;

-- View: Sessões Ativas
CREATE OR REPLACE VIEW v_sessoes_ativas AS
SELECT
    cs.*,
    l.nome as lead_nome,
    l.email as lead_email
FROM chat_sessions cs
LEFT JOIN leads l ON l.id = cs.lead_id
WHERE cs.is_active = TRUE
ORDER BY cs.started_at DESC;

-- ============================================
-- MENSAGEM DE SUCESSO
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '✅ Tabelas espelhadas do Supabase criadas com sucesso!';
    RAISE NOTICE '📊 Tabelas: leads, chat_sessions';
    RAISE NOTICE '📈 Views: v_leads_resumo, v_leads_qualificados, v_sessoes_ativas';
    RAISE NOTICE '🎯 Próximo passo: Atualizar Spark para gravar nessas tabelas';
END $$;
