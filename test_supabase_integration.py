#!/usr/bin/env python3
"""
Teste da Integração Supabase → Kafka → Pipeline SUPERSET
"""

import sys
import json
from supabase_to_kafka import get_supabase_stats, sync_leads_to_kafka, sync_chat_sessions_to_kafka

print("=" * 60)
print("🧪 TESTE: Integração Supabase → Kafka")
print("=" * 60)
print()

# 1. Verificar conexão com Supabase
print("1️⃣ Testando conexão com Supabase...")
print("-" * 60)

stats = get_supabase_stats()

if "error" in stats:
    print(f"❌ Erro ao conectar: {stats['error']}")
    sys.exit(1)

print(f"✅ Conectado ao Supabase!")
print(f"   • Total de leads: {stats['total_leads']}")
print(f"   • Leads qualificados: {stats['qualified_leads']} ({stats['qualification_rate']}%)")
print(f"   • Leads recentes (24h): {stats['recent_leads_24h']}")
print(f"   • Sessões ativas: {stats['active_sessions']}")
print()

# 2. Sincronizar leads (apenas 5 para teste)
if stats['total_leads'] > 0:
    print("2️⃣ Sincronizando 5 leads do Supabase para o Kafka...")
    print("-" * 60)
    
    result = sync_leads_to_kafka(limit=5, hours_ago=720)  # 30 dias
    
    if result.get("status") == "success":
        print(f"✅ Sincronização concluída!")
        print(f"   • Leads encontrados: {result['total_found']}")
        print(f"   • Eventos enviados: {result['total_processed']}")
        print(f"   • Tópico: {result['topic']}")
        
        if result.get('summary'):
            summary = result['summary']
            print(f"   • Score médio: {summary['average_score']:.1f}")
            print(f"   • Score mais alto: {summary['highest_score']}")
            print()
            print("   📊 Por status:")
            for status, count in summary.get('status_breakdown', {}).items():
                print(f"      • {status}: {count}")
    else:
        print(f"❌ Erro: {result.get('error')}")
else:
    print("2️⃣ Skipping sync - nenhum lead disponível")

print()

# 3. Verificar sessões
if stats['active_sessions'] > 0 or stats['total_leads'] > 0:
    print("3️⃣ Sincronizando sessões de chat...")
    print("-" * 60)
    
    result = sync_chat_sessions_to_kafka(limit=5, hours_ago=720)
    
    if result.get("status") == "success":
        print(f"✅ Sessões sincronizadas!")
        print(f"   • Sessões encontradas: {result['total_found']}")
        print(f"   • Eventos enviados: {result['total_processed']}")
    else:
        print(f"❌ Erro: {result.get('error')}")
else:
    print("3️⃣ Skipping sync - nenhuma sessão disponível")

print()
print("=" * 60)
print("✅ TESTES CONCLUÍDOS!")
print("=" * 60)
print()
print("💡 Próximos passos:")
print("   1. Verificar dados no Kafka: docker exec kafka kafka-console-consumer --topic eventos --bootstrap-server localhost:9092")
print("   2. Consultar Postgres: psql -U superset -d superset -c 'SELECT * FROM eventos_raw ORDER BY timestamp DESC LIMIT 5;'")
print("   3. Usar MCP: python superset_mcp.py")
print()
