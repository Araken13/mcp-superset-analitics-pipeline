# 🤖 Servidor MCP SUPERSET - Documentação Completa

## 📖 Índice

1. [Visão Geral](#visão-geral)
2. [Instalação](#instalação)
3. [Ferramentas Disponíveis](#ferramentas-disponíveis)
4. [Guia de Uso](#guia-de-uso)
5. [Troubleshooting](#troubleshooting)
6. [Arquitetura](#arquitetura)

---

## 🎯 Visão Geral

O **Servidor MCP SUPERSET** é uma interface de controle baseada em MCP (Model Context Protocol) que permite gerenciar e monitorar o pipeline de dados em tempo real através de linguagem natural ou chamadas programáticas.

### Capacidades

- 👁️ **Observabilidade**: Monitore o status de todos os serviços (Kafka, Spark, Postgres, Elasticsearch)
- 💾 **Acesso a Dados**: Consulte dados processados no Postgres e Elasticsearch
- 🕹️ **Controle**: Reinicie serviços e injete eventos de teste
- 🧪 **Simulação**: Teste o pipeline com dados sintéticos

---

## 🚀 Instalação

### Pré-requisitos

- Python 3.12+
- Docker e Docker Compose
- WSL2 (se estiver no Windows)

### Passo 1: Configurar Ambiente Virtual

```bash
cd ~/SUPERSET

# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente virtual
source venv/bin/activate
```

### Passo 2: Instalar Dependências

```bash
pip install -r requirements.txt
```

**Nota importante**: O projeto usa `kafka-python-ng` (versão mantida) em vez de `kafka-python` (descontinuada). Isso garante compatibilidade com Python 3.12+.

### Passo 3: Iniciar o Pipeline

```bash
# Subir todos os containers
docker-compose up -d

# Aguardar serviços ficarem prontos (30-60s)
docker-compose ps

# Criar tabelas no banco
./init_database.sh

# (Opcional) Inicializar Superset
./init_superset.sh
```

---

## 🛠️ Ferramentas Disponíveis

### Categoria: Observabilidade

#### `get_pipeline_status()`

Retorna o status de saúde de todos os containers.

**Retorno:**

```
🟢 **superset**: running (running)
🟢 **kafka**: running (running)
🟢 **spark-worker-1**: running (running)
🟢 **elasticsearch**: running (running)
🟢 **spark-master**: running (running)
🟢 **postgres**: running (running)
```

**Limitações**: Requer acesso ao socket Docker (`/var/run/docker.sock`). No Windows, execute dentro do WSL.

---

#### `check_kafka_lag()`

Verifica conectividade com Kafka e lista tópicos disponíveis.

**Retorno:**

```
✅ Kafka acessível. Tópicos encontrados: eventos
```

**Uso**: Diagnóstico rápido de problemas de conectividade com Kafka.

---

#### `get_spark_metrics()`

Obtém métricas do Spark Master via API REST.

**Retorno:**

```
⚡ Spark Master (ALIVE): 1 Workers ativos, 0 Aplicações rodando.
```

**Porta**: `http://localhost:8080/json/`

---

### Categoria: Acesso a Dados

#### `query_raw_events(limit=5)`

Consulta os últimos N eventos brutos no Postgres.

**Parâmetros:**

- `limit` (int): Número de eventos a retornar (padrão: 5)

**Retorno:**

```python
{
  'id': 'dc1e621b-bdfa-462f-9cef-9c07a964aa02',
  'usuario': 'manual_user',
  'evento': 'teste_mcp',
  'valor': 123.45,
  'timestamp': datetime(2025, 12, 4, 9, 45, 52),
  'categoria': 'teste_manual',
  'processado_em': datetime(2025, 12, 4, 12, 45, 52)
}
```

**Tabela consultada**: `eventos_raw`

---

#### `search_elasticsearch(query, index="eventos")`

Busca documentos no Elasticsearch usando sintaxe Lucene.

**Parâmetros:**

- `query` (str): Query string (ex: `categoria:ecommerce AND valor:>500`)
- `index` (str): Nome do índice (padrão: `eventos`)

**Exemplo:**

```python
search_elasticsearch("evento:compra", index="eventos")
```

---

### Categoria: Controle & Simulação

#### `restart_service(service_name)`

Reinicia um container específico.

**Parâmetros:**

- `service_name` (str): Nome do serviço (ex: `spark-worker-1`, `kafka`)

**Retorno:**

```
🔄 Serviço 'spark-worker-1' reiniciado com sucesso!
```

**Uso**: Recuperação rápida de serviços travados.

---

#### `inject_event(evento_tipo, valor, usuario="manual_user")`

Injeta um evento manual no Kafka para teste.

**Parâmetros:**

- `evento_tipo` (str): Tipo do evento (ex: `compra`, `login`)
- `valor` (float): Valor monetário associado
- `usuario` (str): Identificador do usuário (opcional)

**Retorno:**

```json
✅ Evento injetado com sucesso: {
  "id": "8f385f27-7a41-459b-bea8-05718b6abe48",
  "usuario": "manual_user",
  "evento": "teste_mcp",
  "valor": 123.45,
  "timestamp": "2025-12-04T10:36:06.147737",
  "categoria": "teste_manual"
}
```

**Fluxo**: Kafka → Spark Streaming → Postgres/Elasticsearch

---

## 📘 Guia de Uso

### Modo 1: Teste Programático

Execute o script de teste incluído:

```bash
python test_mcp.py
```

Este script testa todas as ferramentas sequencialmente.

---

### Modo 2: Servidor MCP

Inicie o servidor para uso com clientes MCP:

```bash
# Ativar venv
source venv/bin/activate

# Iniciar servidor
mcp run superset_mcp.py
```

O servidor ficará disponível via stdio para clientes MCP (como Claude Desktop, Continue, etc.).

---

### Modo 3: Importação Direta

Use as ferramentas em seus próprios scripts:

```python
from superset_mcp import (
    get_pipeline_status,
    inject_event,
    query_raw_events
)

# Verificar status
status = get_pipeline_status()
print(status)

# Injetar evento de teste
inject_event(evento_tipo="compra", valor=250.00, usuario="teste123")

# Consultar dados
eventos = query_raw_events(limit=10)
print(eventos)
```

---

## 🔧 Troubleshooting

### Problema: `ModuleNotFoundError: No module named 'kafka.vendor.six.moves'`

**Causa**: Versão antiga do `kafka-python` (2.0.2) incompatível com Python 3.12+.

**Solução**:

```bash
pip uninstall kafka-python
pip install kafka-python-ng
```

---

### Problema: `Error while fetching server API version: module 'socket' has no attribute 'AF_UNIX'`

**Causa**: Tentativa de acessar socket Docker do Windows (não suportado).

**Solução**: Execute o script dentro do WSL:

```bash
wsl
cd ~/SUPERSET
source venv/bin/activate
python test_mcp.py
```

---

### Problema: `externally-managed-environment`

**Causa**: Python 3.12+ no Ubuntu 24.04 não permite instalação global de pacotes.

**Solução**: Use ambiente virtual (venv):

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### Problema: Containers não sobem (`docker compose up` falha)

**Diagnóstico**:

```bash
# Ver logs de erro
docker-compose logs

# Verificar se buildx está disponível
docker buildx version
```

**Solução alternativa**:

```bash
# Usar build tradicional
DOCKER_BUILDKIT=0 docker-compose up -d --build
```

---

### Problema: Spark Job não processa dados

**Diagnóstico**:

```bash
# Verificar se o job está rodando
docker exec spark-master ps aux | grep spark

# Ver logs do Spark
docker logs spark-master
```

**Solução**: Submeter o job manualmente:

```bash
docker cp spark_app.py spark-master:/opt/spark-apps/
docker exec -it spark-master bin/spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.7.0,org.elasticsearch:elasticsearch-spark-30_2.12:8.11.0 \
  /opt/spark-apps/spark_app.py
```

---

## 🏗️ Arquitetura

### Fluxo de Dados

```
┌─────────────┐
│   Produtor  │ (kafka_producer.py ou inject_event)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Kafka    │ (Tópico: eventos)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│Spark Stream │ (spark_app.py)
└──────┬──────┘
       │
       ├──────────────┬─────────────┐
       ▼              ▼             ▼
┌──────────┐   ┌──────────┐  ┌──────────┐
│ Postgres │   │Postgres  │  │Elastic-  │
│eventos_  │   │eventos_  │  │search    │
│raw       │   │agregados │  │          │
└──────────┘   └──────────┘  └──────────┘
       │              │             │
       ▼              ▼             ▼
┌──────────┐   ┌──────────┐  ┌──────────┐
│ Superset │   │ Superset │  │  Kibana  │
│Dashboards│   │Dashboards│  │          │
└──────────┘   └──────────┘  └──────────┘
```

### Componentes do MCP Server

```
superset_mcp.py
├── Observabilidade
│   ├── get_pipeline_status() → Docker API
│   ├── check_kafka_lag() → Kafka Admin API
│   └── get_spark_metrics() → Spark REST API
│
├── Dados
│   ├── query_raw_events() → Postgres (psycopg2)
│   └── search_elasticsearch() → Elasticsearch REST API
│
└── Controle
    ├── restart_service() → Docker API
    └── inject_event() → Kafka Producer API
```

---

## 📊 Portas e Endpoints

| Serviço        | Porta  | URL                          | Credenciais       |
|----------------|--------|------------------------------|-------------------|
| Spark Master   | 8080   | <http://localhost:8080>        | -                 |
| Spark Worker   | 8081   | <http://localhost:8081>        | -                 |
| Superset       | 8088   | <http://localhost:8088>        | admin / admin     |
| Kibana         | 5601   | <http://localhost:5601>        | -                 |
| PgAdmin        | 5050   | <http://localhost:5050>        | <admin@admin.com>   |
| Elasticsearch  | 9200   | <http://localhost:9200>        | -                 |
| Kafka          | 29092  | localhost:29092              | -                 |
| Postgres       | 5432   | localhost:5432               | superset/superset |

---

## 🎓 Exemplos Práticos

### Exemplo 1: Monitoramento Completo

```python
from superset_mcp import *

# 1. Verificar saúde do sistema
print(get_pipeline_status())

# 2. Verificar Kafka
print(check_kafka_lag())

# 3. Verificar Spark
print(get_spark_metrics())
```

### Exemplo 2: Teste End-to-End

```python
from superset_mcp import inject_event, query_raw_events
import time

# Injetar evento
inject_event("compra_teste", 99.99, "user_123")

# Aguardar processamento (Spark processa em micro-batches)
time.sleep(5)

# Verificar se chegou no banco
eventos = query_raw_events(limit=1)
print(eventos)
```

### Exemplo 3: Recuperação de Falha

```python
from superset_mcp import get_pipeline_status, restart_service

# Verificar status
status = get_pipeline_status()

# Se algum serviço estiver down, reiniciar
if "🔴" in status:
    restart_service("spark-worker-1")
```

---

## 📝 Notas de Desenvolvimento

### Testado em

- ✅ Ubuntu 24.04 (WSL2)
- ✅ Python 3.12.3
- ✅ Docker 27.x
- ✅ kafka-python-ng 2.2.3

### Limitações Conhecidas

- `get_pipeline_status()` não funciona no PowerShell (apenas WSL/Linux)
- Requer que o pipeline esteja rodando para testes completos
- Elasticsearch pode demorar ~60s para ficar "Healthy" na primeira inicialização

---

## 🤝 Contribuindo

Para adicionar novas ferramentas ao MCP:

1. Adicione a função decorada com `@mcp.tool()` em `superset_mcp.py`
2. Documente a função com docstring clara
3. Adicione testes em `test_mcp.py`
4. Atualize esta documentação

---

## 📄 Licença

Este projeto é parte do pipeline SUPERSET de dados em tempo real.
