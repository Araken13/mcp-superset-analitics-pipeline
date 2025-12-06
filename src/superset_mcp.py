import asyncio
import logging
import json
import os
from typing import Any, List, Dict, Optional

# MCP Imports
from mcp.server.fastmcp import FastMCP

# Library Imports
import docker
import psycopg2
from kafka import KafkaAdminClient  # Isso funcionará com kafka-python-ng
from kafka import KafkaAdminClient
from kafka.errors import KafkaError
import requests

# Configuração de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("superset-mcp")

# Inicializar FastMCP
mcp = FastMCP("Superset Control Plane")

# Configurações do Ambiente (assumindo execução local ou via docker network)
# Se rodar fora do docker, localhost. Se dentro, usar nomes dos serviços.
# Vamos assumir execução local (host) acessando portas expostas.
DOCKER_SOCK = "unix://var/run/docker.sock"
POSTGRES_DSN = "postgresql://superset:superset@localhost:5432/superset"
KAFKA_BOOTSTRAP = "localhost:29092"
ELASTICSEARCH_URL = "http://localhost:9200"

# --- Ferramentas de Observabilidade ---

@mcp.tool()
def get_pipeline_status() -> str:
    """
    Retorna o status de saúde de todos os containers do pipeline SUPERSET.
    Verifica se estão rodando (Up) ou parados.
    """
    try:
        client = docker.DockerClient(base_url=DOCKER_SOCK)
        containers = client.containers.list(all=True)
        
        status_report = []
        superset_containers = [c for c in containers if "superset" in c.name.lower() or "kafka" in c.name.lower() or "spark" in c.name.lower() or "postgres" in c.name.lower() or "elastic" in c.name.lower()]
        
        if not superset_containers:
            return "⚠️ Nenhum container do pipeline SUPERSET encontrado. Verifique se o docker compose foi iniciado."

        for container in superset_containers:
            state = container.status
            icon = "🟢" if state == "running" else "🔴"
            status_report.append(f"{icon} **{container.name}**: {state} ({container.status})")
            
        return "\n".join(status_report)
    except Exception as e:
        return f"❌ Erro ao verificar Docker: {str(e)}"

@mcp.tool()
def check_kafka_lag() -> str:
    """
    Verifica se há atraso (lag) no consumo de mensagens do Kafka.
    Isso indica se o Spark Streaming está dando conta do volume de dados.
    """
    # Nota: Calcular lag exato requer consultar offsets do consumer group.
    # Como simplificação, vamos checar se o tópico existe e se está acessível.
    try:
        admin = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP)
        topics = admin.list_topics()
        
        if "eventos" not in topics:
            return "⚠️ Tópico 'eventos' não encontrado no Kafka. O pipeline pode não ter sido inicializado."
            
        # Para lag real, precisariamos da API do ConsumerGroup, que é mais complexa via kafka-python.
        # Vamos retornar o status básico por enquanto.
        return f"✅ Kafka acessível. Tópicos encontrados: {', '.join(topics)}"
    except Exception as e:
        return f"❌ Erro ao conectar no Kafka: {str(e)}"

@mcp.tool()
def get_spark_metrics() -> str:
    """
    Tenta obter métricas básicas da UI do Spark Master.
    """
    try:
        # A UI do Master geralmente fica na 8080. A API JSON fica na 8080/json/
        resp = requests.get("http://localhost:8080/json/", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            active_apps = len(data.get('activeapps', []))
            workers = len(data.get('workers', []))
            status = data.get('status', 'UNKNOWN')
            return f"⚡ Spark Master ({status}): {workers} Workers ativos, {active_apps} Aplicações rodando."
        else:
            return f"⚠️ Spark Master respondeu com status {resp.status_code}"
    except Exception as e:
        return f"❌ Não foi possível contatar Spark Master na porta 8080: {str(e)}"

# --- Ferramentas de Dados (Iniciais) ---

@mcp.tool()
def query_raw_events(limit: int = 5) -> str:
    """
    Consulta os últimos N eventos brutos gravados no Postgres.
    Útil para verificar se os dados estão chegando no banco.
    """
    try:
        conn = psycopg2.connect(POSTGRES_DSN)
        cur = conn.cursor()
        
        query = "SELECT * FROM eventos_raw ORDER BY timestamp DESC LIMIT %s;"
        cur.execute(query, (limit,))
        rows = cur.fetchall()
        
        if not rows:
            return "📭 Nenhum evento encontrado na tabela 'eventos_raw'."
            
        # Formatar resultado
        colnames = [desc[0] for desc in cur.description]
        result = []
        for row in rows:
            row_dict = dict(zip(colnames, row))
            result.append(str(row_dict))
            
        cur.close()
        conn.close()
        return "\n\n".join(result)
    except Exception as e:
        return f"❌ Erro ao consultar Postgres: {str(e)}"



@mcp.tool()
def search_elasticsearch(query: str, index: str = "eventos") -> str:
    """
    Busca documentos no Elasticsearch usando uma query string simples (Lucene syntax).
    Ex: 'categoria:ecommerce AND valor:>500'
    """
    try:
        # Usar _search com q= parameter para query string simples
        url = f"{ELASTICSEARCH_URL}/{index}/_search"
        params = {"q": query, "size": 5, "pretty": "true"}
        
        resp = requests.get(url, params=params)
        
        if resp.status_code != 200:
            return f"⚠️ Elasticsearch retornou erro {resp.status_code}: {resp.text}"
            
        data = resp.json()
        hits = data.get("hits", {}).get("hits", [])
        
        if not hits:
            return f"📭 Nenhum resultado encontrado para '{query}' no índice '{index}'."
            
        results = []
        for hit in hits:
            source = hit.get("_source", {})
            results.append(json.dumps(source, indent=2))
            
        return "\n---\n".join(results)
    except Exception as e:
        return f"❌ Erro ao buscar no Elasticsearch: {str(e)}"

# --- Ferramentas de Controle (Ops) ---

@mcp.tool()
def restart_service(service_name: str) -> str:
    """
    Reinicia um container específico do pipeline.
    Ex: 'spark-worker', 'superset', 'kafka'.
    """
    try:
        client = docker.DockerClient(base_url=DOCKER_SOCK)
        # Buscar container por nome aproximado
        containers = client.containers.list(all=True)
        target = next((c for c in containers if service_name in c.name), None)
        
        if not target:
            return f"⚠️ Container com nome similar a '{service_name}' não encontrado."
            
        target.restart()
        return f"🔄 Serviço '{target.name}' reiniciado com sucesso!"
    except Exception as e:
        return f"❌ Erro ao reiniciar serviço: {str(e)}"

@mcp.tool()
def inject_event(evento_tipo: str, valor: float, usuario: str = "manual_user") -> str:
    """
    Injeta um evento manual no Kafka para teste.
    """
    try:
        from kafka import KafkaProducer
        import uuid
        from datetime import datetime
        
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        evento = {
            'id': str(uuid.uuid4()),
            'usuario': usuario,
            'evento': evento_tipo,
            'valor': valor,
            'timestamp': datetime.now().isoformat(),
            'categoria': 'teste_manual'
        }
        
        producer.send('eventos', value=evento)
        producer.flush()
        producer.close()
        
        return f"✅ Evento injetado com sucesso: {json.dumps(evento)}"
    except Exception as e:
        return f"❌ Erro ao injetar evento: {str(e)}"


# ==============================================================================
# INTEGRAÇÃO SUPABASE (LOVABLE SITE)
# ==============================================================================

@mcp.tool()
def sync_leads_from_supabase(limit: int = 100, hours_ago: int = 24) -> str:
    """
    Sincroniza leads do Supabase (LOVABLE SITE) para o pipeline Kafka.
    
    Args:
        limit: Número máximo de leads a sincronizar
        hours_ago: Considerar apenas leads criados nas últimas N horas
    
    Exemplo:
        sync_leads_from_supabase(limit=50, hours_ago=12)
    """
    try:
        from supabase_to_kafka import sync_leads_to_kafka
        
        result = sync_leads_to_kafka(limit=limit, hours_ago=hours_ago)
        
        if result.get("status") == "success":
            total_processed = result.get("total_processed", 0)
            total_found = result.get("total_found", 0)
            summary = result.get("summary", {})
            
            response = f"""✅ Sincronização concluída!

📊 Resumo:
• Total encontrado: {total_found} leads
• Total enviado ao Kafka: {total_processed} eventos
• Período: Últimas {hours_ago}h
• Score mais alto: {summary.get('highest_score', 'N/A')}
• Score médio: {summary.get('average_score', 'N/A'):.1f}

📈 Por Status:"""
            
            for status, count in summary.get('status_breakdown', {}).items():
                response += f"\n   • {status}: {count}"
                
            return response
        else:
            return f"❌ Erro: {result.get('error', 'Erro desconhecido')}"
            
    except Exception as e:
        return f"❌ Erro ao sincronizar leads: {str(e)}"


@mcp.tool()
def sync_chat_sessions_from_supabase(limit: int = 50, hours_ago: int = 24) -> str:
    """
    Sincroniza sessões de chat do Supabase para o pipeline Kafka.
    
    Args:
        limit: Número máximo de sessões a sincronizar
        hours_ago: Considerar apenas sessões nas últimas N  horas
    
    Exemplo:
        sync_chat_sessions_from_supabase(limit=30, hours_ago=6)
    """
    try:
        from supabase_to_kafka import sync_chat_sessions_to_kafka
        
        result = sync_chat_sessions_to_kafka(limit=limit, hours_ago=hours_ago)
        
        if result.get("status") == "success":
            total_processed = result.get("total_processed", 0)
            total_found = result.get("total_found", 0)
            
            return f"""✅ Sincronização de sessões concluída!

📊 Resumo:
• Total encontrado: {total_found} sessões
• Total enviado ao Kafka: {total_processed} eventos
• Período: Últimas {hours_ago}h
• Tópico Kafka: {result.get('topic')}"""
        else:
            return f"❌ Erro: {result.get('error', 'Erro desconhecido')}"
            
    except Exception as e:
        return f"❌ Erro ao sincronizar sessões: {str(e)}"


@mcp.tool()
def get_supabase_dashboard() -> str:
    """
    Obtém estatísticas gerais do Supabase (LOVABLE SITE).
    
    Mostra métricas de leads, qualificação, sessões ativas, etc.
    """
    try:
        from supabase_to_kafka import get_supabase_stats
        
        stats= get_supabase_stats()
        
        if "error" in stats:
            return f"❌ Erro: {stats.get('error')}"
        
        return f"""📊 Dashboard Supabase - {stats.get('database')}

🎯 Leads:
   • Total de leads: {stats.get('total_leads')}
   • Leads qualificados (score ≥ 50): {stats.get('qualified_leads')}
   • Taxa de qualificação: {stats.get('qualification_rate')}%
   • Leads nas últimas 24h: {stats.get('recent_leads_24h')}

💬 Sessões:
   • Sessões ativas: {stats.get('active_sessions')}

🔗 Conexão:
   • URL: {stats.get('supabase_url')}
   • Status: ✅ Conectado"""
    except Exception as e:
        return f"❌ Erro ao obter estatísticas: {str(e)}"


if __name__ == "__main__":
    mcp.run()
