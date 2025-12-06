#!/usr/bin/env python3
"""
🔐 Supabase RLS Security Audit Tool
=============================================
Verifica o status de segurança do banco Supabase e identifica vulnerabilidades.

Uso:
    python supabase_rls_audit.py
"""

import os
from supabase import create_client
from dotenv import load_dotenv
from tabulate import tabulate
from colorama import init, Fore, Style

# Inicializar colorama
init()

# Carregar .env
load_dotenv()

# Conectar ao Supabase (usando service_role para acesso admin)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print(f"{Fore.RED}❌ Credenciais Supabase não configuradas no .env{Style.RESET_ALL}")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def print_header(title):
    """Imprime cabeçalho formatado"""
    print(f"\n{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{title.center(70)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")

def print_section(title):
    """Imprime título de seção"""
    print(f"\n{Fore.YELLOW}📊 {title}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'-'*70}{Style.RESET_ALL}")

def check_rls_status():
    """Verifica status de RLS em todas as tabelas"""
    print_header("🔐 AUDITORIA DE SEGURANÇA - SUPABASE RLS")
    
    # Query para verificar RLS
    query = """
        SELECT 
            schemaname as schema,
            tablename as tabela,
            rowsecurity as rls_ativo
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename;
    """
    
    try:
        result = supabase.rpc('execute_sql', {'query': query}).execute()
        
        if result.data:
            # Formatar dados
            tables_data = []
            vulnerable_count = 0
            
            for row in result.data:
                rls_status = "✅ ATIVO" if row['rls_ativo'] else "❌ DESATIVADO"
                security = "Protegido" if row['rls_ativo'] else "⚠️ VULNERÁVEL"
                
                if not row['rls_ativo']:
                    vulnerable_count += 1
                
                tables_data.append([
                    row['schema'],
                    row['tabela'],
                    rls_status,
                    security
                ])
            
            # Mostrar tabela
            print_section("1. STATUS DE RLS POR TABELA")
            print(tabulate(tables_data, headers=['Schema', 'Tabela', 'RLS Status', 'Segurança'], tablefmt='grid'))
            
            # Resumo
            total = len(tables_data)
            protected = total - vulnerable_count
            percentage = (protected / total * 100) if total > 0 else 0
            
            print_section("2. RESUMO GERAL")
            summary = [
                ["Tabelas com RLS", f"{Fore.GREEN}{protected}{Style.RESET_ALL}"],
                ["Tabelas sem RLS", f"{Fore.RED}{vulnerable_count}{Style.RESET_ALL}"],
                ["Total de Tabelas", total],
                ["% Protegido", f"{percentage:.1f}%"]
            ]
            print(tabulate(summary, tablefmt='plain'))
            
            # Listar tabelas vulneráveis
            if vulnerable_count > 0:
                print_section("⚠️  3. TABELAS VULNERÁVEIS")
                print(f"{Fore.RED}As seguintes tabelas NÃO têm RLS ativado:{Style.RESET_ALL}\n")
                
                for row in tables_data:
                    if "DESATIVADO" in row[2]:
                        print(f"{Fore.RED}🚨 {row[1]}{Style.RESET_ALL}")
                        print(f"   Solução: ALTER TABLE {row[0]}.{row[1]} ENABLE ROW LEVEL SECURITY;\n")
            else:
                print_section("3. TABELAS VULNERÁVEIS")
                print(f"{Fore.GREEN}✅ Nenhuma tabela vulnerável encontrada!{Style.RESET_ALL}")
            
        else:
            print(f"{Fore.YELLOW}⚠️ Nenhuma tabela encontrada no schema 'public'{Style.RESET_ALL}")
            
    except Exception as e:
        # Fallback: tentar via REST API
        print(f"{Fore.YELLOW}⚠️ RPC não disponível. Tentando método alternativo...{Style.RESET_ALL}\n")
        check_via_rest_api()

def check_via_rest_api():
    """Método alternativo: verifica RLS através das tabelas conhecidas"""
    print_section("1. VERIFICAÇÃO DE TABELAS CONHECIDAS")
    
    # Tabelas esperadas no projeto LOVABLE SITE
    known_tables = [
        'leads',
        'chat_sessions',
        'chat_messages',
        'chatbot_analytics'
    ]
    
    results = []
    vulnerable = []
    
    for table in known_tables:
        try:
            # Tentar acessar a tabela
            response = supabase.table(table).select("*", count='exact').limit(0).execute()
            
            # Se conseguir acessar, verificar se há erro de RLS
            if response:
                results.append([
                    table,
                    "✅ Acessível",
                    "⚠️ Verificar políticas RLS"
                ])
            
        except Exception as e:
            error_msg = str(e)
            
            if "row-level security" in error_msg.lower() or "permission denied" in error_msg.lower():
                results.append([
                    table,
                    "🔒 Protegido",
                    "✅ RLS ativo (acesso negado)"
                ])
            elif "does not exist" in error_msg.lower():
                results.append([
                    table,
                    "❓ Não existe",
                    "Tabela não encontrada"
                ])
            else:
                results.append([
                    table,
                    "❌ Erro",
                    error_msg[:50]
                ])
                vulnerable.append(table)
    
    print(tabulate(results, headers=['Tabela', 'Status', 'Observação'], tablefmt='grid'))
    
    # Recomendações
    print_section("💡 RECOMENDAÇÕES")
    
    if vulnerable:
        print(f"{Fore.RED}🚨 AÇÃO NECESSÁRIA:{Style.RESET_ALL}")
        print(f"   {len(vulnerable)} tabela(s) podem estar vulneráveis\n")
        
        for table in vulnerable:
            print(f"{Fore.YELLOW}Ativar RLS em '{table}':{Style.RESET_ALL}")
            print(f"   1. Acesse: Supabase Dashboard → Database → Tables → {table}")
            print(f"   2. Clique em 'Enable RLS'")
            print(f"   3. Crie políticas de acesso apropriadas\n")
    else:
        print(f"{Fore.GREEN}✅ Todas as tabelas parecem estar protegidas ou corretamente configuradas!{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}📝 PRÓXIMOS PASSOS:{Style.RESET_ALL}")
    print("   1. Acesse: https://supabase.com/dashboard → Seu Projeto → Database → Tables")
    print("   2. Verifique cada tabela e ative 'Enable RLS' se necessário")
    print("   3. Crie políticas de acesso (Policies) para cada tabela")
    print("   4. Teste com diferentes roles (anon, authenticated)")

def main():
    """Função principal"""
    try:
        check_rls_status()
        
        # Footer
        print(f"\n{Fore.CYAN}{'='*70}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}✅ Auditoria concluída!{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}💡 DICA: Para segurança máxima:{Style.RESET_ALL}")
        print("   • Ative RLS em TODAS as tabelas")
        print("   • Crie políticas restritivas (auth.uid() = user_id)")
        print("   • Use 'authenticated' role sempre que possível")
        print("   • Evite políticas 'public' sem filtros")
        print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}\n")
        
    except Exception as e:
        print(f"{Fore.RED}❌ Erro na auditoria: {str(e)}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
