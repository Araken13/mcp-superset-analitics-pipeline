-- ============================================================================
-- SUPABASE RLS SECURITY AUDIT SCRIPT
-- ============================================================================
-- Este script verifica o status de segurança do banco de dados Supabase
-- e identifica possíveis vulnerabilidades de RLS (Row Level Security)
-- ============================================================================

\echo '╔══════════════════════════════════════════════════════════════╗'
\echo '║     AUDITORIA DE SEGURANÇA - SUPABASE RLS                    ║'
\echo '╚══════════════════════════════════════════════════════════════╝'
\echo ''

-- ============================================================================
-- 1. VERIFICAR STATUS RLS DE TODAS AS TABELAS
-- ============================================================================

\echo '📊 1. STATUS DE RLS POR TABELA'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'

SELECT 
    schemaname AS schema,
    tablename AS tabela,
    CASE 
        WHEN rowsecurity THEN '✅ ATIVO'
        ELSE '❌ DESATIVADO'
    END AS rls_status,
    CASE 
        WHEN rowsecurity THEN 'Protegido'
        ELSE '⚠️ VULNERÁVEL - Dados expostos!'
    END AS seguranca
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY rowsecurity ASC, schemaname, tablename;

\echo ''

-- ============================================================================
-- 2. CONTAR TABELAS COM/SEM RLS
-- ============================================================================

\echo '📈 2. RESUMO GERAL'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'

SELECT 
    COUNT(*) FILTER (WHERE rowsecurity) AS tabelas_com_rls,
    COUNT(*) FILTER (WHERE NOT rowsecurity) AS tabelas_sem_rls,
    COUNT(*) AS total_tabelas,
    ROUND(
        (COUNT(*) FILTER (WHERE rowsecurity)::NUMERIC / COUNT(*)::NUMERIC) * 100, 
        2
    ) AS percentual_protegido
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema');

\echo ''

-- ============================================================================
-- 3. LISTAR TODAS AS POLÍTICAS RLS EXISTENTES
-- ============================================================================

\echo '🔐 3. POLÍTICAS RLS CONFIGURADAS'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'

SELECT 
    schemaname AS schema,
    tablename AS tabela,
    policyname AS politica,
    CASE cmd
        WHEN 'r' THEN 'SELECT'
        WHEN 'a' THEN 'INSERT'
        WHEN 'w' THEN 'UPDATE'
        WHEN 'd' THEN 'DELETE'
        WHEN '*' THEN 'ALL'
    END AS operacao,
    CASE 
        WHEN roles = '{public}' THEN '🌐 PUBLIC (Todos)'
        WHEN roles = '{authenticated}' THEN '🔑 AUTHENTICATED (Logados)'
        WHEN roles = '{anon}' THEN '👤 ANON (Não logados)'
        ELSE array_to_string(roles, ', ')
    END AS roles,
    CASE 
        WHEN qual IS NOT NULL THEN 'Com condição'
        ELSE 'Sem condição'
    END AS tem_condicao
FROM pg_policies
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY schemaname, tablename, policyname;

\echo ''

-- ============================================================================
-- 4. TABELAS VULNERÁVEIS (SEM RLS)
-- ============================================================================

\echo '⚠️  4. TABELAS VULNERÁVEIS (SEM RLS)'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'

SELECT 
    schemaname AS schema,
    tablename AS tabela,
    '🚨 CRÍTICO' AS severidade,
    'Dados podem ser acessados sem autenticação!' AS risco,
    'ALTER TABLE ' || schemaname || '.' || tablename || ' ENABLE ROW LEVEL SECURITY;' AS solucao_sql
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
AND rowsecurity = false
ORDER BY tablename;

\echo ''

-- ============================================================================
-- 5. TABELAS COM RLS MAS SEM POLÍTICAS
-- ============================================================================

\echo '⚠️  5. TABELAS COM RLS MAS SEM POLÍTICAS'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'

SELECT 
    t.schemaname AS schema,
    t.tablename AS tabela,
    '⚠️ ATENÇÃO' AS severidade,
    'RLS ativo mas sem políticas = NINGUÉM tem acesso!' AS observacao
FROM pg_tables t
LEFT JOIN pg_policies p ON 
    t.schemaname = p.schemaname AND 
    t.tablename = p.tablename
WHERE t.schemaname NOT IN ('pg_catalog', 'information_schema')
AND t.rowsecurity = true
AND p.policyname IS NULL
GROUP BY t.schemaname, t.tablename
ORDER BY t.tablename;

\echo ''

-- ============================================================================
-- 6. POLÍTICAS PERIGOSAS (ACESSO PÚBLICO TOTAL)
-- ============================================================================

\echo '🔥 6. POLÍTICAS POTENCIALMENTE PERIGOSAS'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'

SELECT 
    schemaname AS schema,
    tablename AS tabela,
    policyname AS politica,
    '🔥 ALTO RISCO' AS severidade,
    'Acesso público total sem filtros!' AS problema
FROM pg_policies
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
AND roles = '{public}'
AND qual IS NULL  -- Sem condição WHERE
AND cmd IN ('*', 'r')  -- Permite SELECT ou ALL
ORDER BY tablename, policyname;

\echo ''

-- ============================================================================
-- 7. VERIFICAR PERMISSÕES DE ROLES
-- ============================================================================

\echo '👥 7. PERMISSÕES POR ROLE'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'

SELECT 
    grantee AS role,
    table_schema AS schema,
    table_name AS tabela,
    string_agg(privilege_type, ', ' ORDER BY privilege_type) AS permissoes
FROM information_schema.table_privileges
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
AND grantee IN ('public', 'anon', 'authenticated', 'service_role')
GROUP BY grantee, table_schema, table_name
ORDER BY 
    CASE grantee
        WHEN 'public' THEN 1
        WHEN 'anon' THEN 2
        WHEN 'authenticated' THEN 3
        WHEN 'service_role' THEN 4
    END,
    table_name;

\echo ''

-- ============================================================================
-- 8. RECOMENDAÇÕES DE SEGURANÇA
-- ============================================================================

\echo '💡 8. RECOMENDAÇÕES'
\echo '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'

WITH vulnerabilities AS (
    SELECT COUNT(*) AS count
    FROM pg_tables
    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
    AND rowsecurity = false
),
tables_without_policies AS (
    SELECT COUNT(*) AS count
    FROM pg_tables t
    LEFT JOIN pg_policies p ON t.schemaname = p.schemaname AND t.tablename = p.tablename
    WHERE t.schemaname NOT IN ('pg_catalog', 'information_schema')
    AND t.rowsecurity = true
    AND p.policyname IS NULL
),
public_policies AS (
    SELECT COUNT(*) AS count
    FROM pg_policies
    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
    AND roles = '{public}'
    AND qual IS NULL
)
SELECT 
    CASE 
        WHEN v.count > 0 THEN '🚨 CRÍTICO: ' || v.count || ' tabela(s) SEM RLS - Ativar imediatamente!'
        ELSE '✅ OK: Todas as tabelas têm RLS ativo'
    END AS rls_status,
    CASE 
        WHEN t.count > 0 THEN '⚠️ ATENÇÃO: ' || t.count || ' tabela(s) com RLS mas SEM políticas - Criar políticas!'
        ELSE '✅ OK: Todas as tabelas com RLS têm políticas'
    END AS policies_status,
    CASE 
        WHEN p.count > 0 THEN '🔥 ALERTA: ' || p.count || ' política(s) pública(s) sem filtro - Restringir acesso!'
        ELSE '✅ OK: Nenhuma política pública sem filtro'
    END AS public_access_status
FROM vulnerabilities v, tables_without_policies t, public_policies p;

\echo ''
\echo '╔══════════════════════════════════════════════════════════════╗'
\echo '║                  FIM DA AUDITORIA                            ║'
\echo '╚══════════════════════════════════════════════════════════════╝'
\echo ''
\echo '📝 PRÓXIMOS PASSOS:'
\echo '1. Ativar RLS em tabelas vulneráveis'
\echo '2. Criar políticas para tabelas sem políticas'
\echo '3. Revisar políticas públicas sem filtros'
\echo '4. Testar acesso com diferentes roles (anon, authenticated)'
\echo ''
\echo '💡 DICA: Para ativar RLS em uma tabela:'
\echo '   ALTER TABLE public.sua_tabela ENABLE ROW LEVEL SECURITY;'
\echo ''
\echo '💡 DICA: Para criar uma política básica (exemplo):'
\echo '   CREATE POLICY "Usuários podem ver seus próprios dados"'
\echo '     ON public.sua_tabela FOR SELECT'
\echo '     USING (auth.uid() = user_id);'
\echo ''
