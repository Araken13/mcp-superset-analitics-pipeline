# 🚀 Guia de Instalação e Configuração Automática

## Scripts Criados

### 1. `startup.sh` - Inicialização Automática

Script principal que inicializa todo o pipeline automaticamente.

**O que faz:**

- ✅ Verifica se Docker está rodando
- ✅ Para containers antigos
- ✅ Limpa checkpoints antigos
- ✅ Inicia todos os containers
- ✅ Aguarda containers ficarem healthy
- ✅ Copia e inicia Spark jobs
- ✅ Verifica conectividade de serviços
- ✅ Mostra resumo com URLs de acesso

**Como usar:**

```bash
cd /home/renan3/SUPERSET
chmod +x startup.sh
./startup.sh
```

---

### 2. `healthcheck.sh` - Verificação de Saúde

Script de diagnóstico que verifica todos os componentes.

**O que verifica:**

- 🐳 Todos os containers Docker
- 🔌 Conectividade dos serviços
- ⚡ Spark jobs ativos
- 💾 Dados no Postgres e Elasticsearch

**Como usar:**

```bash
chmod +x healthcheck.sh
./healthcheck.sh
```

**Códigos de saída:**

- `0` - Sistema totalmente operacional
- `1` - Sistema parcialmente operacional (80%+)
- `2` - Sistema com problemas críticos

---

### 3. `superset-pipeline.service` - Serviço Systemd

Arquivo de serviço para inicialização automática ao ligar o computador.

---

## 📋 Instalação da Inicialização Automática

### Opção 1: Systemd (Recomendado para Linux)

**Passo 1: Tornar scripts executáveis**

```bash
cd /home/renan3/SUPERSET
chmod +x startup.sh healthcheck.sh
```

**Passo 2: Copiar serviço para systemd**

```bash
sudo cp superset-pipeline.service /etc/systemd/system/
```

**Passo 3: Habilitar serviço**

```bash
sudo systemctl daemon-reload
sudo systemctl enable superset-pipeline.service
```

**Passo 4: Iniciar serviço (teste)**

```bash
sudo systemctl start superset-pipeline.service
```

**Passo 5: Verificar status**

```bash
sudo systemctl status superset-pipeline.service
```

**Passo 6: Ver logs**

```bash
sudo journalctl -u superset-pipeline.service -f
```

---

### Opção 2: Cron (@reboot)

Se preferir usar cron em vez de systemd:

**Editar crontab:**

```bash
crontab -e
```

**Adicionar linha:**

```cron
@reboot sleep 30 && /home/renan3/SUPERSET/startup.sh >> /tmp/superset-startup.log 2>&1
```

*Nota: O `sleep 30` garante que Docker tenha tempo para iniciar.*

---

### Opção 3: WSL (Windows)

Para WSL, você pode criar um arquivo `.bat` ou usar Task Scheduler do Windows:

**Criar arquivo `start-superset.bat`:**

```batch
@echo off
wsl -d Ubuntu -u renan3 bash -c "cd /home/renan3/SUPERSET && ./startup.sh"
pause
```

**Adicionar ao Task Scheduler:**

1. Abrir Task Scheduler
2. Create Basic Task
3. Trigger: "At startup"
4. Action: "Start a program"
5. Program: `C:\caminho\para\start-superset.bat`

---

## 🛠️ Uso no Dia a Dia

### Iniciar Pipeline Manualmente

```bash
./startup.sh
```

### Verificar Saúde

```bash
./healthcheck.sh
```

### Parar Pipeline

```bash
docker compose down
```

### Reiniciar Um Serviço Específico

```bash
docker restart spark-master
# ou
docker restart postgres
# ou
docker restart elasticsearch
```

### Ver Logs de Um Serviço

```bash
docker logs -f spark-master
# ou
docker logs --tail 100 postgres
```

---

## 📊 Monitoramento via MCP

Depois que o pipeline estiver rodando, você pode usar o MCP para monitoramento:

```bash
# Ativar ambiente
source venv/bin/activate

# Iniciar servidor MCP
python superset_mcp.py
```

**Ferramentas MCP disponíveis:**

- `get_pipeline_status()` - Status de todos os containers
- `check_kafka_lag()` - Lag do Kafka
- `get_spark_metrics()` - Métricas do Spark
- `query_raw_events()` - Consultar Postgres
- `search_elasticsearch()` - Buscar no Elasticsearch

---

## 🔧 Troubleshooting

### Problema: Script não executa

```bash
# Verificar permissões
ls -l startup.sh healthcheck.sh

# Dar permissão de execução
chmod +x startup.sh healthcheck.sh
```

### Problema: Docker não inicia

```bash
# Verificar se Docker está instalado
docker --version

# Iniciar Docker manualmente
sudo service docker start
```

### Problema: Containers não ficam healthy

```bash
# Ver logs de um container específico
docker logs --tail 50 <container_name>

# Reiniciar container problemático
docker restart <container_name>
```

### Problema: Spark job não inicia

```bash
# Verificar se job está rodando
docker exec spark-master curl -s http://localhost:8080/json/ | python3 -c "import sys, json; print(len(json.load(sys.stdin)['activeapps']))"

# Ver logs do Spark
docker logs spark-master --tail 100

# Reiniciar job manualmente
./startup.sh
```

---

## 📝 Logs e Diagnóstico

### Logs do Startup Script

```bash
cat /tmp/superset-startup.log
```

### Logs do Systemd Service

```bash
sudo journalctl -u superset-pipeline.service -n 100
```

### Logs de Containers

```bash
# Todos os containers
docker compose logs --tail=50

# Container específico
docker logs spark-master --tail 100 -f
```

---

## 🎯 URLs de Acesso (Após Inicialização)

| Serviço        | URL                          | Descrição                |
|----------------|------------------------------|--------------------------|
| Superset       | <http://localhost:8088>        | BI e Dashboards          |
| Kibana         | <http://localhost:5601>        | Visualização ES          |
| Spark Master   | <http://localhost:8080>        | Monitorar Jobs           |
| Spark Worker   | <http://localhost:8081>        | Status Worker            |
| Elasticsearch  | <http://localhost:9200>        | API REST                 |
| pgAdmin        | <http://localhost:5050>        | Admin PostgreSQL         |

---

## ✅ Checklist de Validação

Após executar `startup.sh`, verificar:

- [ ] Todos os containers estão `Up`
- [ ] Pelo menos 7 containers estão `(healthy)`
- [ ] Spark Master UI acessível (<http://localhost:8080>)
- [ ] Pelo menos 1 Spark app ativa
- [ ] PostgreSQL aceita conexões
- [ ] Elasticsearch responde
- [ ] Kibana carrega
- [ ] Superset carrega

**Comando rápido:**

```bash
./healthcheck.sh
```

Se tudo passar ✅, o sistema está **100% operacional**!

---

## 📞 Suporte

Se encontrar problemas:

1. Executar `./healthcheck.sh` para diagnóstico
2. Verificar `/tmp/superset-startup.log`
3. Verificar logs dos containers: `docker compose logs`
4. Consultar `README_SISTEMA_COMPLETO.md` para troubleshooting detalhado

---

**Última Atualização:** 2025-12-05  
**Versão:** 1.0
