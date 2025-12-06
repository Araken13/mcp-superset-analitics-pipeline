# 🚀 Sistema SUPERSET - Pipeline de Dados em Tempo Real

## 📊 Visão Geral

Sistema completo de ingestão, processamento e análise de dados em tempo real, integrando múltiplas fontes (Supabase, APIs, eventos manuais) e disponibilizando visualizações através de Superset e Kibana.

### Arquitetura

```
┌─────────────────┐
│  LOVABLE SITE   │
│   (Supabase)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐      ┌─────────────────┐
│  Supabase API   │─────▶│    Kafka     │─────▶│  Spark Stream   │
│   (REST API)    │      │ (Topic:      │      │   Processing    │
└─────────────────┘      │  eventos)    │      └────────┬────────┘
                         └──────────────┘               │
                                                        ├─────────┐
                                                        ▼         ▼
                         ┌──────────────┐      ┌─────────────────┐
                         │  PostgreSQL  │      │ Elasticsearch   │
                         │ (eventos_raw)│      │  (index:eventos)│
                         └──────┬───────┘      └────────┬────────┘
                                │                       │
                         ┌──────▼───────┐      ┌───────▼─────────┐
                         │   Superset   │      │     Kibana      │
                         │ (Dashboards) │      │  (Visualização) │
                         └──────────────┘      └─────────────────┘
```

---

## 🔧 Componentes do Sistema

### 1. **Kafka** (Broker de Mensagens)

- **Porta:** 9092 (externa), 29092 (interna)
- **Função:** Recebe eventos de múltiplas fontes e distribui para consumidores
- **Tópico principal:** `eventos`

### 2. **Spark Streaming** (Processamento)

- **Porta Web UI:** 8080 (Master), 8081 (Worker)
- **Função:** Processa eventos do Kafka em tempo real e grava em Postgres/Elasticsearch
- **Jobs ativos:** `spark_app.py`

### 3. **PostgreSQL** (Armazenamento Relacional)

- **Porta:** 5432
- **Banco:** `superset`
- **Usuário/Senha:** `superset/superset`
- **Tabelas principais:**
  - `eventos_raw` - Eventos brutos processados
  - `eventos_agregados` - Eventos agregados por janela de tempo
  - `leads` - Leads do Supabase (estrutura completa)
  - `chat_sessions` - Sessões de chat do chatbot

### 4. **Elasticsearch** (Indexação e Busca)

- **Porta:** 9200 (API), 9300 (Cluster)
- **Função:** Indexação full-text e buscas rápidas
- **Índice:** `eventos`

### 5. **Kibana** (Visualização)

- **Porta:** 5601
- **URL:** <http://localhost:5601>
- **Função:** Dashboards e exploração de dados do Elasticsearch

### 6. **Superset** (BI/Dashboards)

- **Porta:** 8088
- **URL:** <http://localhost:8088>
- **Função:** Business Intelligence e dashboards SQL
- **Login padrão:** Configurar no primeiro acesso

### 7. **Supabase Integration** (Fonte de Dados)

- **Projeto:** LOVABLE SITE - APPNE IA
- **Função:** Sincroniza leads e sessões de chat para o pipeline

---

## 🚀 Como Iniciar o Sistema

### Pré-requisitos

- Docker e Docker Compose instalados
- WSL2 (se no Windows)
- Python 3.12+ com venv

### Passo 1: Iniciar Containers Docker

```bash
cd ~/SUPERSET
docker compose up -d
```

**Aguarde ~30 segundos** para todos os containers ficarem "healthy".

Verificar status:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Passo 2: Ativar Ambiente Python

```bash
cd ~/SUPERSET
source venv/bin/activate
```

### Passo 3: Iniciar Spark Job

```bash
nohup docker exec spark-master bin/spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.7.0,org.elasticsearch:elasticsearch-spark-30_2.12:8.11.0 \
  /opt/spark-apps/spark_app.py > /tmp/spark_job.log 2>&1 &
```

Verificar se está rodando:

```bash
docker exec spark-master curl -s http://localhost:8080/json/ | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Apps ativas: {len(data[\"activeapps\"])}')"
```

Deve retornar: `Apps ativas: 1`

### Passo 4: Testar o Sistema

```bash
# Testar injeção de evento
python -c "from superset_mcp import inject_event; print(inject_event('teste', 100.0, 'sistema'))"

# Aguardar 15s e verificar no Postgres
docker exec postgres psql -U superset -d superset -c "SELECT * FROM eventos_raw ORDER BY processado_em DESC LIMIT 3;"

# Verificar no Elasticsearch
docker exec elasticsearch curl -s "http://localhost:9200/eventos/_count?pretty"
```

---

## 📥 Integração Supabase

### Sincronizar Dados do Supabase

#### Ver Estatísticas

```bash
python supabase_to_kafka.py stats
```

Retorna:

```json
{
  "total_leads": 3,
  "qualified_leads": 2,
  "qualification_rate": 66.67,
  "active_sessions": 20,
  "recent_leads_24h": 0
}
```

#### Sincronizar Leads (últimos 30 dias)

```bash
python -c "from supabase_to_kafka import sync_leads_to_kafka; print(sync_leads_to_kafka(limit=100, hours_ago=720))"
```

#### Sincronizar Sessões de Chat

```bash
python -c "from supabase_to_kafka import sync_chat_sessions_to_kafka; print(sync_chat_sessions_to_kafka(limit=50, hours_ago=720))"
```

### Automatizar Sincronização (Cron)

```bash
# Editar crontab
crontab -e

# Adicionar linha (sincronizar a cada 6 horas)
0 */6 * * * cd /home/renan3/SUPERSET && source venv/bin/activate && python -c "from supabase_to_kafka import sync_leads_to_kafka; sync_leads_to_kafka(100, 12)" >> /tmp/supabase_sync.log 2>&1
```

---

## 📊 Usando o Superset

### Acesso

- **URL:** <http://localhost:8088>
- **Primeiro Acesso:** Criar usuário admin

### Conectar ao Postgres

1. Acesse: **Data → Databases → + Database**
2. Preencha:

   ```
   Database: PostgreSQL
   Host: postgres
   Port: 5432
   Database name: superset
   Username: superset
   Password: superset
   ```

3. Clique em **Test Connection** → **Save**

### Criar Dataset

1. **Data → Datasets → + Dataset**
2. Selecione:
   - Database: `PostgreSQL`
   - Schema: `public`
   - Table: `eventos_raw`
3. **Save**

### Criar Dashboard

1. **Dashboards → + Dashboard**
2. Adicione Charts:
   - **Time Series:** Eventos por categoria ao longo do tempo
   - **Big Number:** Total de eventos hoje
   - **Table:** Últimos 10 leads processados
   - **Pie Chart:** Eventos por origem

### Queries SQL Úteis

```sql
-- Total de eventos por categoria
SELECT categoria, COUNT(*) as total
FROM eventos_raw
GROUP BY categoria
ORDER BY total DESC;

-- Leads qualificados (score >= 50)
SELECT usuario, evento, valor as score, timestamp
FROM eventos_raw
WHERE categoria = 'vendas' AND valor >= 50
ORDER BY timestamp DESC;

-- Eventos nas últimas 24h
SELECT categoria, COUNT(*) as total
FROM eventos_raw
WHERE timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY categoria;

-- Top usuários por valor
SELECT usuario, SUM(valor) as total_valor, COUNT(*) as eventos
FROM eventos_raw
GROUP BY usuario
ORDER BY total_valor DESC
LIMIT 10;
```

---

## 🔍 Usando o Kibana

### Acesso

- **URL:** <http://localhost:5601>
- Primeiro acesso pode demorar ~1 minuto para carregar

### Configurar Index Pattern

1. **Stack Management → Index Patterns → Create Index Pattern**
2. Nome: `eventos*`
3. Time field: `timestamp`
4. **Create**

### Explorar Dados (Discover)

1. **Analytics → Discover**
2. Selecione index pattern: `eventos*`
3. Filtros úteis:

   ```
   categoria:"vendas"
   usuario:"borel@appne.com"
   valor:>50
   timestamp:[now-24h TO now]
   ```

### Criar Visualizações

#### 1. Eventos por Categoria (Pie Chart)

- **Visualize → Create Visualization → Pie**
- Metrics: Count
- Buckets: Split slices → Aggregation: Terms → Field: categoria.keyword

#### 2. Timeline de Eventos (Line Chart)

- **Visualize → Create Visualization → Line**
- Metrics: Count
- Buckets: X-axis → Aggregation: Date Histogram → Field: timestamp

#### 3. Mapa de Calor (Heatmap)

- **Visualize → Create Visualization → Heatmap**
- Metrics: Count
- Buckets:
  - Y-axis: categoria.keyword
  - X-axis: Date histogram (timestamp)

### Criar Dashboard

1. **Analytics → Dashboard → Create Dashboard**
2. **Add from library** (adicione as visualizações criadas)
3. Organize e salve

### Queries DSL Úteis

```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "categoria": "vendas" } },
        { "range": { "valor": { "gte": 50 } } }
      ],
      "filter": [
        { "range": { "timestamp": { "gte": "now-7d" } } }
      ]
    }
  },
  "aggs": {
    "por_dia": {
      "date_histogram": {
        "field": "timestamp",
        "interval": "day"
      }
    }
  }
}
```

---

## 🛠️ Ferramentas MCP (Model Context Protocol)

### Servidor MCP

O projeto inclui um servidor MCP com ferramentas para controle e monitoramento.

#### Iniciar Servidor MCP

```bash
python superset_mcp.py
```

#### Ferramentas Disponíveis

1. **get_pipeline_status()** - Status de todos os containers
2. **check_kafka_lag()** - Verificar atraso no consumo
3. **get_spark_metrics()** - Métricas do Spark
4. **query_raw_events(sql)** - Consultar Postgres
5. **search_elasticsearch(query)** - Buscar no Elasticsearch
6. **inject_event(tipo, valor, usuario)** - Injetar evento de teste
7. **restart_service(service_name)** - Reiniciar serviço
8. **get_supabase_dashboard()** - Stats do Supabase
9. **sync_leads_from_supabase(limit, hours)** - Sincronizar leads
10. **sync_chat_sessions_from_supabase(limit, hours)** - Sincronizar sessões

#### Exemplo de Uso

```python
from superset_mcp import *

# Ver status do pipeline
print(get_pipeline_status())

# Sincronizar 50 leads
print(sync_leads_from_supabase(50, 24))

# Buscar no Elasticsearch
print(search_elasticsearch("categoria:vendas"))
```

---

## 🐛 Troubleshooting

### Problema: Spark Job não está rodando

**Verificar:**

```bash
docker exec spark-master curl -s http://localhost:8080/json/ | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Apps ativas: {len(data[\"activeapps\"])}')"
```

**Solução:**

```bash
# Matar jobs antigos
docker exec spark-master pkill -f spark-submit

# Limpar checkpoint
docker exec spark-master rm -rf /tmp/spark-checkpoint*

# Reiniciar job
nohup docker exec spark-master bin/spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.7.0,org.elasticsearch:elasticsearch-spark-30_2.12:8.11.0 \
  /opt/spark-apps/spark_app.py > /tmp/spark_job.log 2>&1 &
```

### Problema: Dados não aparecem no Postgres

**Verificar Kafka:**

```bash
docker exec kafka kafka-console-consumer --topic eventos --bootstrap-server localhost:9092 --from-beginning --max-messages 5 2>/dev/null
```

**Verificar logs do Spark:**

```bash
tail -50 /tmp/spark_job.log
```

### Problema: Elasticsearch retorna erro

**Reiniciar Elasticsearch:**

```bash
docker restart elasticsearch
# Aguardar 30s
docker logs elasticsearch --tail 20
```

### Problema: Superset não carrega

**Verificar logs:**

```bash
docker logs superset --tail 50
```

**Reiniciar:**

```bash
docker restart superset
```

---

## 📈 Monitoramento

### URLs de Acesso

| Serviço | URL | Descrição |
|---------|-----|-----------|
| Spark Master UI | <http://localhost:8080> | Monitorar jobs Spark |
| Spark Worker UI | <http://localhost:8081> | Status do worker |
| Kibana | <http://localhost:5601> | Visualização Elasticsearch |
| Superset | <http://localhost:8088> | BI e Dashboards |
| Elasticsearch API | <http://localhost:9200> | API REST |
| pgAdmin | <http://localhost:5050> | Admin PostgreSQL |

### Comandos Úteis

```bash
# Ver todos os containers
docker ps

# Logs de um serviço
docker logs <container_name> --tail 50 --follow

# Reiniciar serviço
docker restart <container_name>

# Entrar no container
docker exec -it <container_name> bash

# Ver uso de recursos
docker stats

# Parar tudo
docker compose down

# Iniciar tudo
docker compose up -d
```

---

## 📚 Estrutura de Dados

### Tabela: eventos_raw

```sql
CREATE TABLE eventos_raw (
    id VARCHAR(255) PRIMARY KEY,
    usuario VARCHAR(255),
    evento VARCHAR(255),
    valor DOUBLE PRECISION,
    timestamp TIMESTAMP,
    categoria VARCHAR(255),
    processado_em TIMESTAMP
);
```

### Tabela: leads

```sql
CREATE TABLE leads (
    id UUID PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    telefone VARCHAR(20),
    nome_empresa VARCHAR(255),
    nome_projeto VARCHAR(255),
    interesse TEXT[],
    score_qualificacao INTEGER,
    status_lead VARCHAR(50),
    origem VARCHAR(100),
    utm_source VARCHAR(100),
    utm_medium VARCHAR(100),
    utm_campaign VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    processado_em TIMESTAMP WITH TIME ZONE
);
```

### Índice Elasticsearch: eventos

```json
{
  "id": "uuid",
  "usuario": "email ou identificador",
  "evento": "nome do evento",
  "valor": 123.45,
  "timestamp": 1764938927734,
  "categoria": "vendas|teste_manual|engajamento",
  "processado_em": 1764949727757
}
```

---

## 🔐 Segurança

### Credenciais Padrão

⚠️ **ATENÇÃO:** Altere as credenciais em produção!

#### PostgreSQL

- **Usuário:** `superset`
- **Senha:** `superset`
- **Banco:** `superset`

#### Supabase

- Credenciais em `.env`:
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`

### Recomendações

1. **Alterar senhas** em `.env` antes de deploy
2. **Usar HTTPS** em produção (nginx reverse proxy)
3. **Firewall:** Expor apenas portas necessárias
4. **Backup:** Postgres e Elasticsearch regularmente
5. **Logs:** Rotação automática de logs

---

## 📝 Manutenção

### Backup do Postgres

```bash
docker exec postgres pg_dump -U superset superset > backup_$(date +%Y%m%d).sql
```

### Restore do Postgres

```bash
cat backup_20251205.sql | docker exec -i postgres psql -U superset -d superset
```

### Limpar Dados Antigos

```sql
-- Deletar eventos com mais de 90 dias
DELETE FROM eventos_raw WHERE timestamp < NOW() - INTERVAL '90 days';

-- Vacuum para liberar espaço
VACUUM FULL eventos_raw;
```

### Reindexar Elasticsearch

```bash
# Deletar índice
curl -X DELETE "localhost:9200/eventos"

# Aguardar Spark recriar automaticamente
```

---

## 🚦 Status do Sistema

| Componente | Status | Observações |
|------------|--------|-------------|
| ✅ Kafka | Funcionando | Porta 9092/29092 |
| ✅ Spark Streaming | Funcionando | Job `spark_app.py` |
| ✅ PostgreSQL | Funcionando | Tabelas criadas |
| ✅ Elasticsearch | Funcionando | Índice `eventos` |
| ✅ Kibana | Funcionando | Port 5601 |
| ✅ Superset | Funcionando | Port 8088 |
| ✅ Supabase Integration | Funcionando | Sincronização manual |
| ⚠️ spark_supabase.py | Requer revisão | Não inicia |

---

## 📞 Suporte

### Logs Importantes

- **Spark Job:** `/tmp/spark_job.log`
- **Kafka:** `docker logs kafka`
- **Postgres:** `docker logs postgres`
- **Elasticsearch:** `docker logs elasticsearch`

### Comandos de Diagnóstico

```bash
# Status geral
python test_mcp.py

# Testar Supabase
python supabase_to_kafka.py stats

# Verificar Kafka
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Verificar Postgres
docker exec postgres psql -U superset -d superset -c "\dt"

# Verificar Elasticsearch
curl "localhost:9200/_cat/indices?v"
```

---

**Última Atualização:** 2025-12-05  
**Versão do Sistema:** 1.0  
**Status:** ✅ Produção
