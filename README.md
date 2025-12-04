# 🚀 Pipeline de Dados em Tempo Real

## Kafka + Spark Streaming + Postgres + Elasticsearch + Superset + Kibana

Pipeline completo para processamento de eventos em tempo real, com armazenamento, agregações e visualização.

---

## 📋 Arquitetura

```text
Kafka → Spark Streaming → Postgres + Elasticsearch
                              ↓              ↓
                         Superset        Kibana
```

### Componentes

- **Kafka**: Ingestão de eventos em tempo real
- **Zookeeper**: Coordenação do Kafka
- **Spark**: Processamento e transformação dos dados
- **Postgres**: Armazenamento estruturado
- **Elasticsearch**: Indexação para busca e analytics
- **Superset**: Dashboards e visualizações
- **Kibana**: Visualização de logs e métricas
- **PgAdmin**: Interface para gerenciar Postgres

---

## 🗂️ Estrutura do Projeto

```text
.
├── docker-compose.yml          # Orquestração de containers
├── Dockerfile.spark            # Imagem customizada do Spark
├── spark_app.py               # Pipeline Spark (Kafka → Postgres/ES)
├── kafka_producer.py          # Produtor de eventos de teste
├── create_tables.sql          # Schema do banco de dados
├── init_database.sh           # Script para criar tabelas
├── init_superset.sh           # Script para inicializar Superset
├── run_spark.sh               # Script para executar Spark job
├── test_pipeline.sh           # Teste end-to-end
├── superset_mcp.py            # 🤖 Servidor MCP (NOVO!)
├── test_mcp.py                # Testes do servidor MCP
├── setup_mcp.sh               # Setup automatizado do MCP
├── MCP_DOCUMENTATION.md       # Documentação completa do MCP
└── README.md                  # Este arquivo
```

---

## 🤖 Servidor MCP (Model Context Protocol)

**NOVO!** Este projeto agora inclui um servidor MCP que permite controlar e monitorar o pipeline através de linguagem natural ou chamadas programáticas.

### Início Rápido do MCP

```bash
# Setup automatizado (recomendado)
chmod +x setup_mcp.sh
./setup_mcp.sh

# OU setup manual:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Ferramentas Disponíveis

- 👁️ **Observabilidade**: `get_pipeline_status()`, `check_kafka_lag()`, `get_spark_metrics()`
- 💾 **Dados**: `query_raw_events()`, `search_elasticsearch()`
- 🕹️ **Controle**: `restart_service()`, `inject_event()`

### Teste Rápido

```bash
source venv/bin/activate
python test_mcp.py
```

📖 **Documentação completa**: Veja [MCP_DOCUMENTATION.md](MCP_DOCUMENTATION.md)

---

## 🚀 Início Rápido

### 1. Subir a infraestrutura

```bash
# Subir todos os containers
docker compose up -d --build

# Verificar status
docker compose ps

# Ver logs
docker compose logs -f
```

### 2. Criar tabelas no Postgres

```bash
chmod +x init_database.sh
./init_database.sh
```

### 3. Inicializar Superset

```bash
chmod +x init_superset.sh
./init_superset.sh
```

### 4. Criar tópico Kafka

```bash
docker exec kafka kafka-topics --create \
    --topic eventos \
    --bootstrap-server localhost:9092 \
    --partitions 3 \
    --replication-factor 1
```

### 5. Executar o pipeline Spark

```bash
chmod +x run_spark.sh
./run_spark.sh
```

### 6. Enviar eventos de teste

```bash
# Instalar dependência
pip3 install kafka-python

# Executar produtor
python3 kafka_producer.py
```

---

## 🧪 Teste Completo

Execute o script de teste end-to-end:

```bash
chmod +x test_pipeline.sh
./test_pipeline.sh
```

---

## 🌐 Acessos

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **Spark Master UI** | <http://localhost:8080> | - |
| **Spark Worker UI** | <http://localhost:8081> | - |
| **Superset** | <http://localhost:8088> | admin / admin |
| **Kibana** | <http://localhost:5601> | - |
| **PgAdmin** | <http://localhost:5050> | <admin@admin.com> / admin |
| **Elasticsearch** | <http://localhost:9200> | - |
| **Kafka** | localhost:29092 | - |
| **Postgres** | localhost:5432 | superset / superset |

---

## 📊 Estrutura de Dados

### Tabela: `eventos_raw`

Eventos brutos consumidos do Kafka.

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| id | VARCHAR | ID único do evento |
| usuario | VARCHAR | Identificador do usuário |
| evento | VARCHAR | Tipo de evento |
| valor | DOUBLE | Valor monetário |
| timestamp | TIMESTAMP | Data/hora do evento |
| categoria | VARCHAR | Categoria do evento |
| processado_em | TIMESTAMP | Timestamp do processamento |

### Tabela: `eventos_agregados`

Agregações por janela de tempo (5 minutos).

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| janela_inicio | TIMESTAMP | Início da janela |
| janela_fim | TIMESTAMP | Fim da janela |
| categoria | VARCHAR | Categoria |
| evento | VARCHAR | Tipo de evento |
| total_eventos | BIGINT | Total de eventos |
| valor_medio | DOUBLE | Valor médio |
| valor_total | DOUBLE | Valor total |
| processado_em | TIMESTAMP | Timestamp do processamento |

### Views

- **vw_eventos_ultimas_24h**: Resumo das últimas 24 horas
- **vw_eventos_por_hora**: Eventos agregados por hora (últimos 7 dias)

---

## 🔧 Comandos Úteis

### Docker

```bash
# Parar todos os containers
docker compose down

# Reiniciar serviço específico
docker compose restart spark-master

# Ver logs de um serviço
docker compose logs -f kafka

# Limpar volumes (CUIDADO: apaga dados)
docker compose down -v
```

### Kafka

```bash
# Listar tópicos
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Consumir mensagens
docker exec kafka kafka-console-consumer \
    --topic eventos \
    --bootstrap-server localhost:9092 \
    --from-beginning

# Ver detalhes do tópico
docker exec kafka kafka-topics --describe \
    --topic eventos \
    --bootstrap-server localhost:9092
```

### Postgres

```bash
# Conectar ao banco
docker exec -it postgres psql -U superset -d superset

# Ver tabelas
docker exec postgres psql -U superset -d superset -c "\dt"

# Contar eventos
docker exec postgres psql -U superset -d superset -c \
    "SELECT COUNT(*) FROM eventos_raw;"
```

### Elasticsearch

```bash
# Ver índices
curl http://localhost:9200/_cat/indices?v

# Contar documentos
curl http://localhost:9200/eventos/_count

# Buscar documentos
curl http://localhost:9200/eventos/_search?pretty
```

---

## 📈 Configurando Superset

1. Acesse <http://localhost:8088> (admin/admin)
2. **Adicionar Database**:
   - Settings → Database Connections → + Database
   - SQLAlchemy URI: `postgresql://superset:superset@postgres:5432/superset`
3. **Criar Dataset**:
   - Datasets → + Dataset
   - Selecione as
