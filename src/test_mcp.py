"""
Script de teste para o servidor MCP SUPERSET
Testa as ferramentas diretamente importando o módulo
"""
import sys
sys.path.insert(0, '/home/renan3/SUPERSET')

from superset_mcp import (
    get_pipeline_status,
    check_kafka_lag,
    get_spark_metrics,
    query_raw_events
)

print("=" * 60)
print("TESTE DO SERVIDOR MCP SUPERSET")
print("=" * 60)

print("\n1️⃣ Testando get_pipeline_status():")
print("-" * 60)
result = get_pipeline_status()
print(result)

print("\n\n2️⃣ Testando check_kafka_lag():")
print("-" * 60)
result = check_kafka_lag()
print(result)

print("\n\n3️⃣ Testando get_spark_metrics():")
print("-" * 60)
result = get_spark_metrics()
print(result)

print("\n\n4️⃣ Testando inject_event():")
print("-" * 60)
# Importar a função aqui pois não estava no import inicial
from superset_mcp import inject_event
result = inject_event(evento_tipo="teste_mcp", valor=123.45)
print(result)

print("\n\n5️⃣ Testando query_raw_events(limit=3):")
print("-" * 60)
result = query_raw_events(limit=3)
print(result)

print("\n" + "=" * 60)
print("TESTES CONCLUÍDOS!")
print("=" * 60)
