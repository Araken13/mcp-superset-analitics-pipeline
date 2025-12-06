-- ============================================================================
-- ATIVAR RLS E CRIAR POLÍTICAS DE SEGURANÇA
-- Execute no Supabase: Dashboard → SQL Editor → New Query
-- ============================================================================

-- 1. ATIVAR RLS em todas as tabelas
ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chatbot_analytics ENABLE ROW LEVEL SECURITY;

-- 2. CRIAR POLÍTICAS para service_role (pipeline Spark/Backend)
-- Service role precisa de acesso total para inserir dados

CREATE POLICY "Service role tem acesso total a leads"
  ON public.leads FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role tem acesso total a chat_sessions"
  ON public.chat_sessions FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role tem acesso total a chat_messages"
  ON public.chat_messages FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role tem acesso total a chatbot_analytics"
  ON public.chatbot_analytics FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- 3. BLOQUEAR acesso anon/public (segurança máxima)
-- Apenas service_role (backend) terá acesso
-- Se precisar dar acesso a usuários autenticados, criar políticas específicas depois

-- Nenhuma política adicional = anon/public NÃO têm acesso
-- Isso protege seus dados!
