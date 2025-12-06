# 🚀 Plano de Deploy em VPS - SUPERSET + LOVABLE SITE

**Data:** 2025-12-05  
**Objetivo:** Deploy completo de SUPERSET Pipeline e LOVABLE SITE em VPS  
**Ambiente Existente:** Redis, n8n, Easypanel

---

## 📊 Análise de Recursos

### Containers SUPERSET (Pipeline de Dados)

| Container | RAM | CPU | Disco | Observações |
|-----------|-----|-----|-------|-------------|
| Kafka | 512 MB | 0.5 | 10 GB | Broker de mensagens |
| Zookeeper | 512 MB | 0.5 | 5 GB | Coordenação Kafka |
| Spark Master | 2 GB | 1.0 | 10 GB | Orquestração |
| Spark Worker | 2 GB | 2.0 | 20 GB | Processamento |
| PostgreSQL | 512 MB | 0.5 | 30 GB | Banco principal |
| Elasticsearch | 2 GB | 1.0 | 50 GB | Indexação e busca |
| Kibana | 512 MB | 0.5 | 5 GB | Visualização ES |
| Superset | 1 GB | 0.5 | 10 GB | BI e Dashboards |
| pgAdmin | 256 MB | 0.25 | 2 GB | Admin DB |
| **TOTAL SUPERSET** | **~9.3 GB** | **~7 vCPUs** | **~142 GB** | |

### LOVABLE SITE (Frontend React)

| Componente | RAM | CPU | Disco | Observações |
|------------|-----|-----|-------|-------------|
| Nginx (produção) | 128 MB | 0.25 | 500 MB | Servir build estático |
| Node.js (build) | 1 GB | 0.5 | 2 GB | Apenas build-time |
| **TOTAL SITE** | **~1 GB** | **~0.75 vCPU** | **~2.5 GB** | |

### Infraestrutura Existente

| Serviço | RAM | CPU | Disco | Observações |
|---------|-----|-----|-------|-------------|
| Redis | 256 MB | 0.25 | 2 GB | Cache |
| n8n | 512 MB | 0.5 | 5 GB | Automação |
| Easypanel | 512 MB | 0.5 | 5 GB | Painel controle |
| **TOTAL EXISTENTE** | **~1.3 GB** | **~1.25 vCPU** | **~12 GB** | |

### Sistema Operacional + Overhead

| Componente | RAM | CPU | Disco |
|------------|-----|-----|-------|
| Ubuntu Server | 1 GB | 0.5 | 10 GB |
| Docker Engine | 512 MB | 0.25 | 5 GB |
| Monitoramento | 256 MB | 0.25 | 5 GB |
| Logs | - | - | 20 GB |
| **TOTAL SISTEMA** | **~1.8 GB** | **~1 vCPU** | **~40 GB** |

---

## 💻 Hardware Recomendado

### ✅ Configuração MÍNIMA (Não Recomendada)

- **RAM:** 12 GB
- **vCPU:** 6 cores
- **Disco:** 200 GB SSD
- **Banda:** 2 TB/mês
- **Custo estimado:** $40-60/mês
- ⚠️ **Risco:** Sistema pode ficar lento em picos de uso

### ✅ Configuração RECOMENDADA (Ideal)

- **RAM:** 16 GB
- **vCPU:** 8 cores
- **Disco:** 250 GB SSD NVMe
- **Banda:** 5 TB/mês
- **Custo estimado:** $80-120/mês
- ✅ **Vantagens:** Estabilidade garantida, espaço para crescimento

### 🚀 Configuração PREMIUM (Future-proof)

- **RAM:** 32 GB
- **vCPU:** 12 cores
- **Disco:** 500 GB SSD NVMe
- **Banda:** Ilimitada
- **Custo estimado:** $150-200/mês
- 🎯 **Vantagens:** Suporta crescimento 3x, alta disponibilidade

---

## 🏢 Provedores Recomendados

### 1. DigitalOcean (Recomendado)

**Droplet: CPU-Optimized 16GB**

- 16 GB RAM / 8 vCPUs
- 250 GB SSD
- $144/mês
- ✅ Excelente documentação
- ✅ Backups automáticos (+20%)
- ✅ Snapshots gratuitos

**Link:** <https://www.digitalocean.com/pricing/droplets>

### 2. Vultr (Melhor custo-benefício)

**Cloud Compute: 16GB**

- 16 GB RAM / 6 vCPUs
- 320 GB SSD
- $96/mês
- ✅ Mais barato
- ✅ 25+ localizações
- ✅ NVMe incluído

**Link:** <https://www.vultr.com/pricing/>

### 3. Hetzner (Europa - Mais barato)

**CPX41**

- 16 GB RAM / 8 vCPUs
- 240 GB SSD
- €29,90/mês (~$32/mês)
- ✅ Preço imbatível
- ⚠️ Servidores apenas na Europa
- ✅ Excelente performance

**Link:** <https://www.hetzner.com/cloud>

### 4. AWS Lightsail (Para quem já usa AWS)

**16GB Plan**

- 16 GB RAM / 8 vCPUs
- 320 GB SSD
- $120/mês
- ✅ Integração AWS
- ⚠️ Mais caro
- ✅ Escalabilidade fácil

**Recomendação Final:** **Vultr** (melhor custo-benefício) ou **DigitalOcean** (melhor experiência)

---

## 📋 Plano de Execução - Deploy VPS

### FASE 1: Preparação da VPS (1-2 horas)

#### 1.1. Provisionar VPS

```bash
# Escolher imagem: Ubuntu 22.04 LTS
# Região: Escolher mais próxima (ex: São Paulo, Miami)
# Configurar SSH keys
```

#### 1.2. Configuração Inicial

```bash
# Conectar via SSH
ssh root@SEU_IP_VPS

# Atualizar sistema
apt update && apt upgrade -y

# Criar usuário não-root
adduser deploy
usermod -aG sudo deploy
usermod -aG docker deploy

# Configurar firewall
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 8088/tcp  # Superset (temporário, depois remover)
ufw allow 5601/tcp  # Kibana (temporário)
ufw enable
```

#### 1.3. Instalar Dependências

```bash
# Instalar Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker

# Instalar Docker Compose
apt install docker-compose-plugin -y

# Instalar utilitários
apt install -y git curl wget vim htop
```

#### 1.4. Configurar Swap (Importante!)

```bash
# Criar swap de 8GB (importante para Elasticsearch)
fallocate -l 8G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Configurar swappiness
sysctl vm.swappiness=10
echo 'vm.swappiness=10' >> /etc/sysctl.conf
```

#### 1.5. Otimizar Elasticsearch

```bash
# Aumentar limite de mmap
sysctl -w vm.max_map_count=262144
echo 'vm.max_map_count=262144' >> /etc/sysctl.conf
```

---

### FASE 2: Deploy SUPERSET (2-3 horas)

#### 2.1. Clonar Repositório

```bash
su - deploy
git clone https://github.com/SEU_USUARIO/SUPERSET.git ~/superset
cd ~/superset
```

#### 2.2. Configurar Variáveis de Ambiente

```bash
# Editar .env
cp .env.example .env
vim .env

# Alterar para produção:
# - Senhas fortes
# - URLs públicas
# - SUPABASE_URL e SUPABASE_ANON_KEY
```

#### 2.3. Configurar Docker Compose para Produção

```bash
# Criar docker-compose.prod.yml
vim docker-compose.prod.yml
```

**docker-compose.prod.yml:**

```yaml
version: '3.8'

services:
  # Usar compose original mas adicionar:
  # - restart: always
  # - healthchecks mais agressivos
  # - limits de recursos
  
  spark-master:
    deploy:
      resources:
        limits:
          memory: 2G
    restart: always
    
  elasticsearch:
    deploy:
      resources:
        limits:
          memory: 2.5G
    restart: always
    environment:
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
```

#### 2.4. Iniciar SUPERSET

```bash
# Dar permissão aos scripts
chmod +x startup.sh healthcheck.sh

# Iniciar
./startup.sh

# Verificar
./healthcheck.sh
```

#### 2.5. Configurar Serviço Systemd

```bash
# Copiar service
sudo cp superset-pipeline.service /etc/systemd/system/

# Habilitar
sudo systemctl daemon-reload
sudo systemctl enable superset-pipeline.service
sudo systemctl start superset-pipeline.service
```

---

### FASE 3: Deploy LOVABLE SITE (1 hora)

#### 3.1. Preparar Projeto

```bash
# Clonar repositório
git clone https://github.com/SEU_USUARIO/LOVABLE-SITE.git ~/lovable-site
cd ~/lovable-site

# Instalar dependências
npm install

# Build de produção
npm run build
# Output estará em: ./dist
```

#### 3.2. Configurar Nginx

```bash
# Instalar Nginx
sudo apt install nginx -y

# Configurar site
sudo vim /etc/nginx/sites-available/lovable-site
```

**nginx config:**

```nginx
server {
    listen 80;
    server_name seu-dominio.com www.seu-dominio.com;
    
    root /home/deploy/lovable-site/dist;
    index index.html;
    
    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;
    
    # Cache assets
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

```bash
# Habilitar site
sudo ln -s /etc/nginx/sites-available/lovable-site /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 3.3. Configurar SSL (Let's Encrypt)

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obter certificado
sudo certbot --nginx -d seu-dominio.com -d www.seu-dominio.com

# Auto-renovação já configurada!
```

---

### FASE 4: Configurar Reverse Proxy (1 hora)

#### 4.1. Configurar Nginx para Superset

```nginx
# /etc/nginx/sites-available/superset
server {
    listen 80;
    server_name superset.seu-dominio.com;
    
    location / {
        proxy_pass http://localhost:8088;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 4.2. Configurar Nginx para Kibana

```nginx
# /etc/nginx/sites-available/kibana
server {
    listen 80;
    server_name kibana.seu-dominio.com;
    
    location / {
        proxy_pass http://localhost:5601;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### 4.3. SSL para Subdomínios

```bash
sudo certbot --nginx -d superset.seu-dominio.com
sudo certbot --nginx -d kibana.seu-dominio.com
```

#### 4.4. Fechar Portas Diretas

```bash
# Remover acesso direto às portas
sudo ufw delete allow 8088/tcp
sudo ufw delete allow 5601/tcp

# Manter apenas 80, 443, 22
```

---

### FASE 5: Monitoramento e Logs (1 hora)

#### 5.1. Configurar Logrotate

```bash
sudo vim /etc/logrotate.d/superset
```

```conf
/tmp/superset-startup.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
```

#### 5.2. Monitoramento com ctop

```bash
# Instalar ctop (top para containers)
sudo wget https://github.com/bcicen/ctop/releases/download/0.7.7/ctop-0.7.7-linux-amd64 -O /usr/local/bin/ctop
sudo chmod +x /usr/local/bin/ctop

# Usar
ctop
```

#### 5.3. Alertas de Disco

```bash
# Cron para verificar espaço
crontab -e

# Adicionar:
0 */6 * * * /home/deploy/superset/healthcheck.sh || echo "SUPERSET HEALTH CHECK FAILED" | mail -s "Alert" seu@email.com
```

---

### FASE 6: Backup e Recuperação (1 hora)

#### 6.1. Backup Automático Postgres

```bash
vim ~/backup-postgres.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/deploy/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

docker exec postgres pg_dump -U superset superset | gzip > $BACKUP_DIR/superset_$DATE.sql.gz

# Manter apenas últimos 7 dias
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
```

```bash
chmod +x ~/backup-postgres.sh

# Cron diário às 3h
crontab -e
0 3 * * * /home/deploy/backup-postgres.sh
```

#### 6.2. Snapshot da VPS

```bash
# Na interface do provedor:
# - DigitalOcean: Enable automated snapshots (weekly)
# - Vultr: Enable automatic backups
# - Hetzner: Create manual snapshots before changes
```

---

## 🔒 Segurança

### Checklist de Segurança

- [ ] SSH key-only (desabilitar senha)
- [ ] Firewall configurado (ufw)
- [ ] Fail2ban instalado
- [ ] SSL/TLS em todos os endpoints
- [ ] Senhas fortes no .env
- [ ] Backup automático configurado
- [ ] Atualizações automáticas de segurança
- [ ] Monitoramento de logs
- [ ] Rate limiting no Nginx
- [ ] CORS configurado apropriadamente

### Fail2ban

```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## 📊 Checklist Pós-Deploy

### Validação SUPERSET

- [ ] Acessar Superset via <https://superset.seu-dominio.com>
- [ ] Conectar dataset Postgres
- [ ] Criar dashboard de teste
- [ ] Verificar Kibana <https://kibana.seu-dominio.com>
- [ ] Testar query no Elasticsearch
- [ ] Injetar evento de teste via MCP
- [ ] Verificar evento no Postgres
- [ ] Verificar evento no Elasticsearch

### Validação LOVABLE SITE

- [ ] Acessar <https://seu-dominio.com>
- [ ] Verificar carregamento rápido
- [ ] Testar todas as páginas
- [ ] Verificar responsividade mobile
- [ ] Testar integração com Supabase
- [ ] Verificar chatbot funcionando

### Validação Infraestrutura

- [ ] Todos os containers UP e healthy
- [ ] Spark job rodando
- [ ] Healthcheck retorna 100%
- [ ] Backup automático funcionando
- [ ] SSL válido em todos os domínios
- [ ] Firewall bloqueando portas desnecessárias

---

## 📈 Otimizações de Performance

### PostgreSQL

```sql
-- postgresql.conf
shared_buffers = 2GB
effective_cache_size = 6GB
maintenance_work_mem = 512MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

### Elasticsearch

```yaml
# elasticsearch.yml
indices.memory.index_buffer_size: 20%
indices.fielddata.cache.size: 40%
```

### Nginx

```nginx
# Aumentar worker connections
worker_processes auto;
worker_connections 4096;

# Habilitar HTTP/2
listen 443 ssl http2;
```

---

## 💰 Estimativa de Custo Mensal

| Item | Custo (USD) |
|------|-------------|
| VPS 16GB (Vultr) | $96 |
| Domínio (.com) | $12/ano = $1 |
| Backups VPS (+20%) | $19 |
| SSL (Let's Encrypt) | Grátis |
| Monitoramento (opcional) | $0-15 |
| **Total Mensal** | **~$115-130** |

**Retorno:** Com pipeline de dados completo + site profissional + infraestrutura escalável.

---

## 📞 Suporte e Manutenção

### Manutenção Semanal

- Verificar `./healthcheck.sh`
- Revisar logs de erro
- Verificar espaço em disco

### Manutenção Mensal

- Atualizar containers Docker
- Revisar métricas de performance
- Testar restore de backup

### Comandos Úteis

```bash
# Ver uso de disco
df -h

# Ver uso de RAM
free -h

# Ver containers
docker ps

# Ver logs
docker compose logs --tail 100

# Reiniciar serviço
sudo systemctl restart superset-pipeline
```

---

**Próximos Passos:**

1. Escolher provedor VPS
2. Provisionar servidor
3. Seguir FASE 1 do plano

**Tempo Total Estimado:** 8-10 horas
**Nível de Dificuldade:** Intermediário
**Recomendação:** Executar em fim de semana para testes
