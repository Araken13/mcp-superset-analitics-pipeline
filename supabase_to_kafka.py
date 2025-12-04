"""
🔗 Supabase to Kafka Bridge - SUPERSET MCP Tool
================================================
Consome dados do Supabase (LOVABLE SITE) e alimenta o pipeline Kafka.

Tabelas disponíveis:
- leads: Informações de leads capturados pelo chatbot
- chat_sessions: Sessões de conversação
- chat_messages: Mensagens individuais
- chatbot_analytics: Métricas agregadas

Uso:
    from supabase_to_kafka import sync_leads_to_kafka
    
    # Sincronizar leads novos
    sync_leads_to_kafka(limit=100)
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from kafka import KafkaProducer
from supabase import create_client, Client

# Configuração
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Credenciais Supabase (do workspace LOVABLE SITE)
SUPABASE_URL = "https://lpdskhiqmufonnnlmemg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxwZHNraGlxbXVmb25ubmxtZW1nIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQyMzc0NjEsImV4cCI6MjA3OTgxMzQ2MX0.pdjLSvqsp2DsmajcofarW9xIGx24Sf7oDH6rpCwzt2Q"

# Kafka config
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:29092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "eventos")

# Cliente Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def transform_lead_to_event(lead: Dict) -> Dict:
    """
    Transforma um lead do Supabase no formato de evento do pipeline.
    
    Formato Supabase (leads):
        {
            "id": "uuid",
            "nome": "João Silva",
            "email": "joao@example.com",
            "telefone": "+5511999999999",
            "nome_empresa": "Tech Corp",
            "nome_projeto": "Sistema Web",
            "interesse": ["desenvolvimento", "consultoria"],
            "score_qualificacao": 75,
            "status_lead": "qualificado",
            "created_at": "2025-12-04T10:30:00",
            "utm_source": "google",
            ...
        }
    
    Formato Pipeline (eventos):
        {
            "id": "uuid",
            "usuario": "joao@example.com",
            "evento": "lead_captado",
            "valor": 75.0,
            "timestamp": "2025-12-04T10:30:00",
            "categoria": "vendas",
            "metadata": {...}
        }
    """
    return {
        "id": lead.get("id"),
        "usuario": lead.get("email"),
        "evento": f"lead_{lead.get('status_lead', 'novo')}",
        "valor": float(lead.get("score_qualificacao", 0)),
        "timestamp": lead.get("created_at", datetime.now().isoformat()),
        "categoria": "vendas",
        "metadata": {
            "nome": lead.get("nome"),
            "telefone": lead.get("telefone"),
            "empresa": lead.get("nome_empresa"),
            "projeto": lead.get("nome_projeto"),
            "interesses": lead.get("interesse", []),
            "origem": lead.get("origem", "chatbot"),
            "utm_source": lead.get("utm_source"),
            "utm_medium": lead.get("utm_medium"),
            "utm_campaign": lead.get("utm_campaign"),
            "localizacao": lead.get("localizacao"),
        }
    }


def transform_session_to_event(session: Dict, messages_count: int = 0) -> Dict:
    """Transforma uma sessão de chat em evento."""
    return {
        "id": session.get("id"),
        "usuario": session.get("lead_id") or "anonimo",
        "evento": "chat_session",
        "valor": float(messages_count),
        "timestamp": session.get("started_at", datetime.now().isoformat()),
        "categoria": "engajamento",
        "metadata": {
            "total_messages": session.get("total_messages", 0),
            "duration_seconds": session.get("duration_seconds", 0),
            "nivel_interesse": session.get("nivel_interesse", "baixo"),
            "intencao_detectada": session.get("intencao_detectada"),
            "is_active": session.get("is_active", False),
        }
    }


def sync_leads_to_kafka(
    limit: int = 100,
    hours_ago: int = 24,
    status_filter: Optional[str] = None
) -> Dict[str, any]:
    """
    Sincroniza leads do Supabase para o Kafka.
    
    Args:
        limit: Número máximo de leads a sincronizar
        hours_ago: Considerar apenas leads criados nas últimas N horas
        status_filter: Filtrar por status ('novo', 'qualificado', etc.)
    
    Returns:
        Dict com estatísticas da sincronização
    """
    try:
        # Calcular timestamp de corte
        since = (datetime.now() - timedelta(hours=hours_ago)).isoformat()
        
        # Construir query
        query = supabase.table("leads").select("*").gte("created_at", since)
        
        if status_filter:
            query = query.eq("status_lead", status_filter)
        
        # Buscar leads
        response = query.order("created_at", desc=True).limit(limit).execute()
        leads = response.data
        
        if not leads:
            return {
                "status": "success",
                "total_processed": 0,
                "message": f"Nenhum lead encontrado nas últimas {hours_ago}h"
            }
        
        # Criar produtor Kafka
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=3
        )
        
        # Enviar eventos
        sent_count = 0
        for lead in leads:
            try:
                event = transform_lead_to_event(lead)
                future = producer.send(KAFKA_TOPIC, value=event)
                result = future.get(timeout=10)  # Aguardar confirmação
                sent_count += 1
                logger.info(f"✅ Lead enviado: {lead.get('email')} (score: {lead.get('score_qualificacao')})")
            except Exception as e:
                logger.error(f"❌ Erro ao enviar lead {lead.get('id')}: {str(e)}")
        
        producer.flush()
        producer.close()
        
        return {
            "status": "success",
            "total_processed": sent_count,
            "total_found": len(leads),
            "period_hours": hours_ago,
            "topic": KAFKA_TOPIC,
            "summary": {
                "highest_score": max([l.get("score_qualificacao", 0) for l in leads]),
                "average_score": sum([l.get("score_qualificacao", 0) for l in leads]) / len(leads),
                "status_breakdown": _count_by_status(leads)
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na sincronização: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


def sync_chat_sessions_to_kafka(
    limit: int = 50,
    hours_ago: int = 24,
    min_messages: int = 0
) -> Dict[str, any]:
    """
    Sincroniza sessões de chat do Supabase para o Kafka.
    
    Args:
        limit: Número máximo de sessões a sincronizar
        hours_ago: Considerar apenas sessões nas últimas N horas
        min_messages: Filtrar sessões com pelo menos N mensagens
    
    Returns:
        Dict com estatísticas da sincronização
    """
    try:
        since = (datetime.now() - timedelta(hours=hours_ago)).isoformat()
        
        # Buscar sessões
        query = (
            supabase.table("chat_sessions")
            .select("*")
            .gte("started_at", since)
        )
        
        if min_messages > 0:
            query = query.gte("total_messages", min_messages)
        
        response = query.order("started_at", desc=True).limit(limit).execute()
        sessions = response.data
        
        if not sessions:
            return {
                "status": "success",
                "total_processed": 0,
                "message": f"Nenhuma sessão encontrada nas últimas {hours_ago}h"
            }
        
        # Criar produtor
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all',
            retries=3
        )
        
        # Enviar eventos
        sent_count = 0
        for session in sessions:
            try:
                event = transform_session_to_event(
                    session,
                    messages_count=session.get("total_messages", 0)
                )
                producer.send(KAFKA_TOPIC, value=event)
                sent_count += 1
                logger.info(f"✅ Sessão enviada: {session.get('id')} ({session.get('total_messages')} msgs)")
            except Exception as e:
                logger.error(f"❌ Erro ao enviar sessão {session.get('id')}: {str(e)}")
        
        producer.flush()
        producer.close()
        
        return {
            "status": "success",
            "total_processed": sent_count,
            "total_found": len(sessions),
            "period_hours": hours_ago,
            "topic": KAFKA_TOPIC
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na sincronização: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


def get_supabase_stats() -> Dict[str, any]:
    """
    Obtém estatísticas gerais do Supabase.
    
    Returns:
        Dict com métricas das tabelas
    """
    try:
        # Total de leads
        leads_response = supabase.table("leads").select("*", count="exact").execute()
        total_leads = leads_response.count
        
        # Leads qualificados (score >= 50)
        qualified_response = (
            supabase.table("leads")
            .select("*", count="exact")
            .gte("score_qualificacao", 50)
            .execute()
        )
        qualified_leads = qualified_response.count
        
        # Sessões ativas
        active_sessions = (
            supabase.table("chat_sessions")
            .select("*", count="exact")
            .eq("is_active", True)
            .execute()
        ).count
        
        # Leads nas últimas 24h
        since_24h = (datetime.now() - timedelta(hours=24)).isoformat()
        recent_leads = (
            supabase.table("leads")
            .select("*", count="exact")
            .gte("created_at", since_24h)
            .execute()
        ).count
        
        return {
            "total_leads": total_leads,
            "qualified_leads": qualified_leads,
            "qualification_rate": round(qualified_leads / total_leads * 100, 2) if total_leads > 0 else 0,
            "active_sessions": active_sessions,
            "recent_leads_24h": recent_leads,
            "supabase_url": SUPABASE_URL.replace("https://", ""),
            "database": "LOVABLE SITE - APPNE IA"
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao obter estatísticas: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


def _count_by_status(leads: List[Dict]) -> Dict[str, int]:
    """Helper para contar leads por status."""
    counts = {}
    for lead in leads:
        status = lead.get("status_lead", "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


# CLI para testes rápidos
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        print("\n📊 Estatísticas do Supabase:")
        print(json.dumps(get_supabase_stats(), indent=2))
    
    elif len(sys.argv) > 1 and sys.argv[1] == "sync-leads":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        print(f"\n🔄 Sincronizando até {limit} leads...")
        result = sync_leads_to_kafka(limit=limit)
        print(json.dumps(result, indent=2))
    
    elif len(sys.argv) > 1 and sys.argv[1] == "sync-sessions":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        print(f"\n🔄 Sincronizando até {limit} sessões...")
        result = sync_chat_sessions_to_kafka(limit=limit)
        print(json.dumps(result, indent=2))
    
    else:
        print("""
🔗 Supabase to Kafka Bridge - Usage:

    python supabase_to_kafka.py stats             # Ver estatísticas
    python supabase_to_kafka.py sync-leads 100   # Sincronizar 100 leads
    python supabase_to_kafka.py sync-sessions 50  # Sincronizar 50 sessões
        """)
