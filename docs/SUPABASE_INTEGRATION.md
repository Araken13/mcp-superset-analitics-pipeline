# 🔗 Integração Supabase → Pipeline SUPERSET

Esta integração permite consumir dados do **Supabase (LOVABLE SITE)** e alimentar o pipeline de dados em tempo real do SUPERSET.

---

## 📊 Fluxo de Dados

```text
LOVABLE SITE (Web) → Supabase → Bridge Python → Kafka → Spark → Postgres/Elasticsearch
```

### Dados Capturados

- **Leads**: Informações de contatos capturados pelo chatbot
- **Chat Sessions**: Sessões de conversação com métricas
- **Chat Messages**: Mensagens individuais (opcional)
- **Analytics**: Métricas agregadas do chatbot

---

## 🚀 Início Rápido

### 1. Instalar Dependências

```bash
# Ativar venv
source venv/bin/activate

# Instalar cliente Supabase
pip install supabase
```

### 2. Verificar Conexão

```bash
python supabase_to_kafka.py stats
```

**Saída esperada:**
```json
{
  "total_leads": 42,
  "qualified_leads": 15,
  "qualification_rate": 35.71,
  "active_sessions": 3,
  "recent_leads_24h": 5,
  "supabase_url": "lpdskhiqmufonnnlmemg.supabase.co",
  "database": "LOVABLE SITE - APPNE IA"
}
```

### 3. Sincronizar Dados

```bash
# Sincronizar leads (últimas 24h, máximo 100)
python supabase_to_kafka.py sync-leads 100

# Sincronizar sessões de chat
python supabase_to_kafka.py sync-sessions 50
```

---

## 🛠️ Ferramentas MCP Disponíveis

### `get_supabase_dashboard()`

Obtém estatísticas gerais do Supabase.

**Exemplo de saída:**
```
📊 Dashboard Supabase - LOVABLE SITE - APPNE IA

🎯 Leads:
   • Total de leads: 42
   • Leads qualificados (score ≥ 50): 15
   • Taxa de qualificação: 35.71%
   • Leads nas últimas 24h: 5

💬 Sessões:
   • Sessões ativas: 3

🔗 Conexão:
   • URL: lpdskhiqmufonnnlmemg.supabase.co
   • Status: ✅ Conectado
```

---

### `sync_leads_from_supabase(limit=100, hours_ago=24)`

Sincroniza leads do Supabase para o Kafka.

**Parâmetros:**
- `limit`: Número máximo de leads (padrão: 100)
- `hours_ago`: Janela de tempo em horas (padrão: 24)

**Exemplo:**
```python
from superset_mcp import sync_leads_from_supabase

result = sync_leads_from_supabase(limit=50, hours_ago=12)
print(result)
```

**Saída:**
```
✅ Sincronização concluída!

📊 Resumo:
• Total encontrado: 12 leads
• Total enviado ao Kafka: 12 eventos
• Período: Últimas 12h
• Score mais alto: 85
• Score médio: 62.3

📈 Por Status:
   • qualificado: 7
   • novo: 3
   • em_contato: 2
```

---

### `sync_chat_sessions_from_supabase(limit=50, hours_ago=24)`

Sincroniza sessões de chat do Supabase para o Kafka.

**Parâmetros:**
- `limit`: Número máximo de sessões (padrão: 50)
- `hours_ago`: Janela de tempo em horas (padrão: 24)

**Exemplo:**
```python
from superset_mcp import sync_chat_sessions_from_supabase

result = sync_chat_sessions_from_supabase(limit=30, hours_ago=6)
print(result)
```

---

## 📋 Estrutura de Dados

### Lead (Supabase)
```json
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
  "origem": "chatbot",
  "utm_source": "google",
  "created_at": "2025-12-04T10:30:00"
}
```

### Evento Transformado (Kafka)
```json
{
  "id": "uuid",
  "usuario": "joao@example.com",
  "evento": "lead_qualificado",
  "valor": 75.0,
  "timestamp": "2025-12-04T10:30:00",
  "categoria": "vendas",
  "metadata": {
    "nome": "João Silva",
    "empresa": "Tech Corp",
    "projeto": "Sistema Web",
    "interesses": ["desenvolvimento", "consultoria"],
    "origem": "chatbot",
    "utm_source": "google"
  }
}
```

---

## 🔄 Sincronização Automática

Para sincronizar dados periodicamente, use um cron job ou systemd timer:

### Opção 1: Cron (a cada hora)

```bash
# Editar crontab
crontab -e

# Adicionar linha:
0 * * * * cd /home/renan3/SUPERSET && source venv/bin/activate && python supabase_to_kafka.py sync-leads 100 >> /tmp/supabase_sync.log 2>&1
```

### Opção 2: Script Python com Loop

Criar `sync_daemon.py`:
```python
import time
from supabase_to_kafka import sync_leads_to_kafka, sync_chat_sessions_to_kafka

while True:
    print("Iniciando sincronização...")
    
    # Sync leads
    sync_leads_to_kafka(limit=100, hours_ago=1)
    
    # Sync sessions
    sync_chat_sessions_to_kafka(limit=50, hours_ago=1)
    
    print("Aguardando próxima execução (3600s)...")
    time.sleep(3600)  # 1 hora
```

Rodar em background:
```bash
nohup python sync_daemon.py > sync_daemon.log 2>&1 &
```

---

## 📈 Análise de Dados

Após sincronizar, os dados estarão disponíveis em:

### 1. Postgres (Dados Brutos)

```sql
-- Ver últimos leads processados
SELECT * FROM eventos_raw 
WHERE categoria = 'vendas' 
ORDER BY timestamp DESC 
LIMIT 10;

-- Estatísticas por status de lead
SELECT 
    metadata->>'status_lead' as status,
    COUNT(*) as total,
    AVG(valor::numeric) as score_medio
FROM eventos_raw
WHERE categoria = 'vendas'
GROUP BY metadata->>'status_lead';
```

### 2. Elasticsearch

```bash
# Buscar leads qualificados
curl "http://localhost:9200/eventos/_search?q=categoria:vendas AND evento:lead_qualificado&pretty"

# Agregação por origem
curl -X GET "localhost:9200/eventos/_search?pretty" -H 'Content-Type: application/json' -d'
{
  "size": 0,
  "aggs": {
    "por_origem": {
      "terms": {
        "field": "metadata.origem.keyword"
      }
    }
  }
}'
```

### 3. Superset/Kibana

Acesse os dashboards para visualizações:
- **Superset**: http://localhost:8088
- **Kibana**: http://localhost:5601

---

## 🐛 Troubleshooting

### Erro: "No module named 'supabase'"

```bash
source venv/bin/activate
pip install supabase
```

### Erro: "Connection refused" (Kafka)

Verificar se Kafka está rodando:
```bash
docker ps | grep kafka
docker logs kafka
```

### Erro: "Invalid credentials" (Supabase)

Verificar credenciais em `supabase_to_kafka.py`:
- `SUPABASE_URL`
- `SUPABASE_KEY`

### Leads não aparecem no Postgres

1. Verificar se o Spark Job está rodando:
   ```bash
   docker logs spark-master | grep "KafkaSparkPostgresPipeline"
   ```

2. Consultar tópico Kafka diretamente:
   ```bash
   docker exec kafka kafka-console-consumer \
     --topic eventos \
     --bootstrap-server localhost:9092 \
     --from-beginning \
     --max-messages 10
   ```

---

##  Exemplo de Uso Completo

```bash
# 1. Ativar ambiente
cd ~/SUPERSET
source venv/bin/activate

# 2. Verificar pipeline está rodando
docker compose ps

# 3. Ver estatísticas do Supabase
python supabase_to_kafka.py stats

# 4. Sincronizar últimas 24h
python supabase_to_kafka.py sync-leads 100

# 5. Verificar dados no Postgres
psql -U superset -d superset -c "SELECT COUNT(*) FROM eventos_raw WHERE categoria='vendas';"

# 6. Usar ferramentas MCP
python -c "from superset_mcp import get_supabase_dashboard; print(get_supabase_dashboard())"
```

---

## 📝 Credenciais

**Supabase (LOVABLE SITE):**
- URL: `https://lpdskhiqmufonnnlmemg.supabase.co`
- Project ID: `lpdskhiqmufonnnlmemg`
- Anon Key: (veja `env.txt` no workspace LOVABLE SITE)

**Tabelas Disponíveis:**
- `leads`
- `chat_sessions`
- `chat_messages`
- `chatbot_analytics`
- `profiles`
- `auth.users`

---

## 🎯 Próximos Passos

1. ✅ Integração básica implementada
2. ⏳ Adicionar filtragem por campos customizados
3. ⏳ Implementar sincronização bidirecional (Postgres → Supabase)
4. ⏳ Criar dashboards específicos para leads
5. ⏳ Alertas automáticos para leads de alto valor

---

**Última Atualização:** 2025-12-04  
**Status:** ✅ Funcional e testado
