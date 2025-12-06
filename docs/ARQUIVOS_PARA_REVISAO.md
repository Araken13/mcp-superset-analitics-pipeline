# 🔍 Arquivos que Precisam de Revisão - SUPERSET

**Data da Análise:** 2025-12-05  
**Status Geral do Sistema:** ✅ Funcional (com ressalvas)

---

## 🔴 CRÍTICO - Requer Correção Imediata

### 1. `spark_supabase.py`

**Status:** ❌ Não funcional  
**Problema:** Job não inicia quando submetido ao Spark  
**Impacto:** Não consegue processar dados do Supabase na tabela `leads` (estrutura completa)

**Erros Identificados:**

- Job é submetido mas não aparece na Spark Master UI
- Sem erros visíveis nos logs
- Possível problema no código Python ou dependências

**Solução Sugerida:**

1. Revisar o código line-by-line
2. Testar localmente antes de submeter
3. Verificar schema do Kafka vs schema esperado pelo código
4. Adicionar logging detalhado

**Workaround Atual:**

- Usar `spark_app.py` (que grava em `eventos_raw`)
- Leads do Supabase ficam gravados em `eventos_raw`, não na tabela `leads`

**Arquivo:**

```python
# Localização: /home/renan3/SUPERSET/spark_supabase.py
# Última modificação: 2025-12-04
```

---

## ⚠️ ATENÇÃO - Funcionando mas com Issues

### 2. `spark_app.py`

**Status:** ✅ Funcional (com duplicação)  
**Problema:** Criando duplicatas no Elasticsearch  
**Impacto:** Baixo - Postgres está protegido por PK, apenas Elasticsearch tem duplicatas

**Detalhes:**

- Grava 1x no Postgres (correto - PK impede duplicação)
- Grava 3x no Elasticsearch (incorreto)
- Causa: Múltiplos jobs rodaram simultaneamente em testes

**Solução Sugerida:**

1. Adicionar verificação de job rodando antes de submeter novo
2. Implementar `mode("append")` com upsert no Elasticsearch
3. Limpar índice Elasticsearch e reprocessar

**Código Problemático:**

```python
# Em spark_app.py, linha ~180-200
df_parsed.writeStream \
    .format("org.elasticsearch.spark.sql") \
    .outputMode("append") \
    .option("checkpointLocation", "/tmp/checkpoint-elasticsearch") \
    .option("es.resource", "eventos") \
    .start()
```

**Solução:**

```python
# Adicionar opção de upsert por ID
.option("es.mapping.id", "id") \
.option("es.write.operation", "upsert")
```

---

### 3. Checkpoints do Spark

**Status:** ⚠️ Requer limpeza  
**Problema:** Checkpoints antigos causam conflitos  
**Impacto:** Médio - Novos jobs podem não processar dados antigos

**Localização:**

- `/tmp/spark-checkpoint-supabase`
- `/tmp/spark-checkpoint-eventos`
- `/tmp/checkpoint-elasticsearch`

**Solução:**

```bash
# Limpar checkpoints antes de reiniciar jobs
docker exec spark-master rm -rf /tmp/spark-checkpoint*
docker exec spark-master rm -rf /tmp/checkpoint-*
```

**Recomendação:**

- Implementar limpeza automática de checkpoints antigos
- Usar path com timestamp: `/tmp/checkpoint-eventos-$(date +%Y%m%d)`

---

## 📝 DOCUMENTAÇÃO - Faltante ou Incompleta

### 4. `MCP_DOCUMENTATION.md`

**Status:** ✅ Existe mas desatualizado  
**Problema:** Não menciona ferramentas de Supabase  
**Impacto:** Baixo - Usuários podem não saber como sincronizar

**Atualizar:**

- Adicionar seção sobre `sync_leads_from_supabase()`
- Adicionar seção sobre `sync_chat_sessions_from_supabase()`
- Adicionar seção sobre `get_supabase_dashboard()`

### 5. `SUPABASE_INTEGRATION.md`

**Status:** ✅ Existe e atualizado  
**Problema:** Nenhum  
**Ação:** Manter atualizado

### 6. `README.md` (principal)

**Status:** ⚠️ Básico demais  
**Problema:** Não explica como usar Superset/Kibana  
**Impacto:** Médio - Curva de aprendizado maior

**Ação Tomada:**

- ✅ Criado `README_SISTEMA_COMPLETO.md` com guias detalhados

**Próximo Passo:**

- Mesclar conteúdo relevante no `README.md` principal
- Criar links entre documentações

---

## 🔧 CONFIGURAÇÃO - Requer Padronização

### 7. `.env`

**Status:** ✅ Funcional  
**Problema:** Credenciais em texto claro  
**Impacto:** Alto em produção

**Recomendações:**

1. Usar secret manager em produção
2. Adicionar `.env.example` (sem credenciais reais)
3. Validar variáveis ao iniciar o sistema

**Exemplo `.env.example`:**

```bash
# PostgreSQL
POSTGRES_USER=superset
POSTGRES_PASSWORD=CHANGE_ME
POSTGRES_DB=superset

# Supabase
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=YOUR_KEY_HERE
```

### 8. `docker-compose.yml`

**Status:** ✅ Funcional  
**Problema:** Sem health checks em todos os serviços  
**Impacto:** Baixo - Inicialização pode ter race conditions

**Melhorias Sugeridas:**

```yaml
# Adicionar health check para Kafka
kafka:
  healthcheck:
    test: kafka-broker-api-versions --bootstrap-server localhost:9092
    interval: 10s
    timeout: 10s
    retries: 5
```

---

## 🧪 TESTES - Faltante ou Incompleto

### 9. `test_mcp.py`

**Status:** ✅ Funcional  
**Problema:** Não testa integração Supabase  
**Impacto:** Baixo - Testes manuais necessários

**Adicionar:**

```python
def test_supabase_sync():
    """Testar sincronização do Supabase"""
    from supabase_to_kafka import sync_leads_to_kafka
    result = sync_leads_to_kafka(limit=1, hours_ago=720)
    assert result['status'] == 'success'
    assert result['total_processed'] >= 0
```

### 10. `test_supabase_integration.py`

**Status:** ✅ Existe e funcional  
**Problema:** Nenhum  
**Ação:** Executar regularmente

---

## 📊 MONITORAMENTO - Faltante

### 11. Logs Centralizados

**Status:** ❌ Não implementado  
**Problema:** Logs espalhados em múltiplos locais  
**Impacto:** Médio - Dificulta troubleshooting

**Logs Atuais:**

- Spark: `/tmp/spark_job.log`
- Containers: `docker logs <name>`
- Python: stdout

**Solução Sugerida:**

- Implementar ELK stack (Elasticsearch já existe)
- Ou usar Loki + Grafana
- Centralizar logs em volume Docker

### 12. Métricas de Performance

**Status:** ❌ Não implementado  
**Problema:** Sem visibilidade de throughput, latência  
**Impacto:** Médio - Otimização difícil

**Implementar:**

- Prometheus + Grafana
- JMX exporter para Kafka/Spark
- Métricas customizadas no MCP

---

## 🔄 CI/CD - Faltante

### 13. Pipeline de Deploy

**Status:** ❌ Não existe  
**Problema:** Deploy manual  
**Impacto:** Médio - Risco de erro humano

**Criar:**

- `.github/workflows/test.yml` - Testes automatizados
- `.github/workflows/deploy.yml` - Deploy para produção
- Script de validação pré-deploy

---

## 📋 Checklist de Revisão

### Prioridade ALTA (Fazer Agora)

- [ ] Corrigir `spark_supabase.py` para funcionar
- [ ] Resolver duplicação no Elasticsearch (`spark_app.py`)
- [ ] Limpar checkpoints antigos
- [ ] Criar `.env.example`

### Prioridade MÉDIA (Esta Semana)

- [ ] Atualizar `MCP_DOCUMENTATION.md` com ferramentas Supabase
- [ ] Adicionar testes de integração Supabase
- [ ] Implementar health checks completos no docker-compose
- [ ] Adicionar script de validação de ambiente

### Prioridade BAIXA (Quando Possível)

- [ ] Implementar logs centralizados
- [ ] Adicionar métricas de performance
- [ ] Criar pipeline CI/CD
- [ ] Migrar credenciais para secret manager

---

## 🛠️ Como Aplicar as Correções

### Passo 1: Corrigir spark_supabase.py

```bash
# 1. Revisar código
code /home/renan3/SUPERSET/spark_supabase.py

# 2. Testar localmente
python3 spark_supabase.py

# 3. Resubmeter ao Spark
docker cp spark_supabase.py spark-master:/opt/spark-apps/
docker exec -d spark-master bin/spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,org.postgresql:postgresql:42.7.0 \
  /opt/spark-apps/spark_supabase.py
```

### Passo 2: Corrigir Duplicação Elasticsearch

```bash
# Editar spark_app.py
code /home/renan3/SUPERSET/spark_app.py

# Adicionar na linha ~190:
# .option("es.mapping.id", "id")
# .option("es.write.operation", "upsert")

# Recarregar
docker cp spark_app.py spark-master:/opt/spark-apps/
# Reiniciar job (ver README_SISTEMA_COMPLETO.md)
```

### Passo 3: Limpar Checkpoints

```bash
docker exec spark-master rm -rf /tmp/spark-checkpoint*
docker exec spark-master rm -rf /tmp/checkpoint-*
```

---

## 📞 Próximos Passos

1. ✅ README completo criado
2. ⏳ Corrigir `spark_supabase.py`
3. ⏳ Resolver duplicação Elasticsearch
4. ⏳ Implementar testes automatizados
5. ⏳ Deploy em produção

---

**Responsável pela Revisão:** Time de Desenvolvimento  
**Prazo Sugerido:** 7 dias úteis  
**Prioridade Geral:** MÉDIA-ALTA
