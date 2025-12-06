#!/usr/bin/env python3
"""
Testes Automatizados End-to-End - SUPERSET
Valida fluxo completo: Supabase → Kafka → Spark → Postgres + Elasticsearch
"""

import time
import requests
import psycopg2
import json
from datetime import datetime

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_test(name):
    print(f"\n{Colors.OKBLUE}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{name}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}{'='*60}{Colors.ENDC}")

def print_success(msg):
    print(f"{Colors.OKGREEN}✅ {msg}{Colors.ENDC}")

def print_error(msg):
    print(f"{Colors.FAIL}❌ {msg}{Colors.ENDC}")

def print_warning(msg):
    print(f"{Colors.WARNING}⚠️  {msg}{Colors.ENDC}")

def print_info(msg):
    print(f"{Colors.OKCYAN}ℹ️  {msg}{Colors.ENDC}")


class TestSupabaseIntegration:
    """Testes da integração Supabase"""
    
    def __init__(self):
        self.test_user = f"test_user_{int(time.time())}"
        self.test_id = None
    
    def test_1_supabase_connection(self):
        """1️⃣ Testa conexão com Supabase"""
        print_test("Teste 1: Conexão Supabase")
        
        try:
            from supabase_to_kafka import get_supabase_stats
            stats = get_supabase_stats()
            
            assert "total_leads" in stats, "Campo 'total_leads' ausente"
            assert stats["total_leads"] >= 0, "total_leads deve ser >= 0"
            
            print_success(f"Conexão OK - {stats['total_leads']} leads encontrados")
            print_info(f"Leads qualificados: {stats.get('qualified_leads', 0)}")
            return True
            
        except Exception as e:
            print_error(f"Falha na conexão: {str(e)}")
            return False
    
    def test_2_sync_leads(self):
        """2️⃣ Testa sincronização de leads do Supabase"""
        print_test("Teste 2: Sincronização de Leads")
        
        try:
            from supabase_to_kafka import sync_leads_to_kafka
            result = sync_leads_to_kafka(limit=3, hours_ago=720)
            
            assert result["status"] == "success", "Status deve ser 'success'"
            assert "total_processed" in result, "Campo 'total_processed' ausente"
            
            print_success(f"Sincronização OK - {result['total_processed']} leads processados")
            return True
            
        except Exception as e:
            print_error(f"Falha na sincronização: {str(e)}")
            return False
    
    def test_3_inject_event(self):
        """3️⃣ Testa injeção de evento via MCP"""
        print_test("Teste 3: Injeção de Evento (MCP)")
        
        try:
            from superset_mcp import inject_event
            result = inject_event("test_e2e", 999.99, self.test_user)
            
            # Parse do JSON de retorno
            result_dict = json.loads(result.replace("✅ Evento injetado com sucesso: ", ""))
            self.test_id = result_dict["id"]
            
            assert "id" in result_dict, "Evento deve ter ID"
            assert result_dict["usuario"] == self.test_user, "Usuário incorreto"
            
            print_success(f"Evento injetado - ID: {self.test_id}")
            print_info(f"Usuário: {self.test_user}")
            return True
            
        except Exception as e:
            print_error(f"Falha ao injetar evento: {str(e)}")
            return False
    
    def test_4_wait_for_processing(self):
        """4️⃣ Aguarda processamento pelo Spark"""
        print_test("Teste 4: Aguardando Processamento")
        
        print_info("Aguardando 20 segundos para Spark processar...")
        for i in range(20, 0, -1):
            print(f"\r⏳ {i}s restantes...", end="", flush=True)
            time.sleep(1)
        print()
        print_success("Aguardo concluído!")
        return True
    
    def test_5_verify_postgres(self):
        """5️⃣ Verifica se evento chegou no Postgres"""
        print_test("Teste 5: Verificação no PostgreSQL")
        
        try:
            conn = psycopg2.connect(
                host="localhost", 
                port=5432,
                dbname="superset", 
                user="superset", 
                password="superset"
            )
            cursor = conn.cursor()
            
            # Buscar evento
            cursor.execute(
                "SELECT id, usuario, evento, valor, categoria FROM eventos_raw WHERE usuario=%s ORDER BY processado_em DESC LIMIT 1",
                (self.test_user,)
            )
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result:
                print_success(f"Evento encontrado no Postgres!")
                print_info(f"ID: {result[0]}")
                print_info(f"Usuário: {result[1]}")
                print_info(f"Evento: {result[2]}")
                print_info(f"Valor: {result[3]}")
                return True
            else:
                print_error("Evento NÃO encontrado no Postgres")
                return False
                
        except Exception as e:
            print_error(f"Erro ao consultar Postgres: {str(e)}")
            return False
    
    def test_6_verify_elasticsearch(self):
        """6️⃣ Verifica se evento chegou no Elasticsearch"""
        print_test("Teste 6: Verificação no Elasticsearch")
        
        try:
            # Buscar por usuário
            url = f"http://localhost:9200/eventos/_search"
            query = {
                "query": {
                    "match": {"usuario": self.test_user}
                }
            }
            
            response = requests.post(url, json=query)
            data = response.json()
            
            hits = data.get("hits", {}).get("total", {}).get("value", 0)
            
            if hits > 0:
                print_success(f"Evento encontrado no Elasticsearch!")
                print_info(f"Total de documentos: {hits}")
                
                # Mostrar primeiro hit
                first_hit = data["hits"]["hits"][0]["_source"]
                print_info(f"ID:  {first_hit.get('id')}")
                print_info(f"Usuário: {first_hit.get('usuario')}")
                print_info(f"Evento: {first_hit.get('evento')}")
                return True
            else:
                print_error("Evento NÃO encontrado no Elasticsearch")
                return False
                
        except Exception as e:
            print_error(f"Erro ao consultar Elasticsearch: {str(e)}")
            return False
    
    def test_7_pipeline_health(self):
        """7️⃣ Verifica saúde geral do pipeline"""
        print_test("Teste 7: Saúde do Pipeline")
        
        try:
            from superset_mcp import get_pipeline_status
            status = get_pipeline_status()
            
            # Parse status
            services_up = status.count("Up")
            services_healthy = status.count("healthy")
            
            print_info(f"Serviços UP: {services_up}")
            print_info(f"Serviços HEALTHY: {services_healthy}")
            
            if services_up >= 8:  # Esperamos pelo menos 8 serviços
                print_success("Pipeline saudável!")
                return True
            else:
                print_warning(f"Apenas {services_up} serviços UP (esperado: 9)")
                return False
                
        except Exception as e:
            print_error(f"Erro ao verificar pipeline: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Executa todos os testes"""
        print(f"\n{Colors.HEADER}")
        print("╔══════════════════════════════════════════════════════════╗")
        print("║   TESTES AUTOMATIZADOS - SUPERSET PIPELINE E2E          ║")
        print("║   Data: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "                               ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print(f"{Colors.ENDC}")
        
        tests = [
            self.test_1_supabase_connection,
            self.test_2_sync_leads,
            self.test_3_inject_event,
            self.test_4_wait_for_processing,
            self.test_5_verify_postgres,
            self.test_6_verify_elasticsearch,
            self.test_7_pipeline_health
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print_error(f"Exceção no teste: {str(e)}")
                failed += 1
        
        # Resumo final
        print(f"\n{Colors.HEADER}")
        print("╔══════════════════════════════════════════════════════════╗")
        print("║                    RESUMO DOS TESTES                     ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print(f"{Colors.ENDC}")
        print(f"{Colors.OKGREEN}✅ Testes Passados: {passed}{Colors.ENDC}")
        print(f"{Colors.FAIL}❌ Testes Falhados: {failed}{Colors.ENDC}")
        print(f"📊 Taxa de Sucesso: {(passed/(passed+failed)*100):.1f}%\n")
        
        if failed == 0:
            print(f"{Colors.OKGREEN}{Colors.BOLD}🎉 TODOS OS TESTES PASSARAM! 🎉{Colors.ENDC}\n")
            return 0
        else:
            print(f"{Colors.FAIL}{Colors.BOLD}⚠️  ALGUNS TESTES FALHARAM ⚠️{Colors.ENDC}\n")
            return 1


if __name__ == "__main__":
    import sys
    tester = TestSupabaseIntegration()
    sys.exit(tester.run_all_tests())
