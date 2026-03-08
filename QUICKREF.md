# 📋 Deployment Bot Quick Reference

## Deploy (One Command)

```bash
# From project root
chmod +x scripts/deploy-bot.sh
./scripts/deploy-bot.sh
```

---

## Configuration

```bash
# Create .env.prod
cp .env.prod.example .env.prod
nano .env.prod

# Required:
DB_PASSWORD=secure-password
RBAC_SECRET=secure-secret

# Optional:
HEALTH_CHECK_INTERVAL=30
RECOVERY_ATTEMPTS=3
RECOVERY_DELAY=10
```

---

## Monitoring

```bash
# Real-time logs
docker logs -f vh2-deployment-bot-service

# Service status
docker-compose -f docker-compose.prod.yaml -p vh2-stack ps

# Health history
docker exec vh2-deployment-bot-service \
  tail -f /var/log/deployment_bot/health_snapshots.jsonl
```

---

## Direct Bot Commands

```bash
# Full deploy (build + deploy + monitor)
python deployment_bot.py full-deploy

# Build only
python deployment_bot.py build

# Deploy only
python deployment_bot.py deploy

# Monitor only
python deployment_bot.py monitor --interval 30

# Check status
python deployment_bot.py status

# Recover service
python deployment_bot.py recover --service orchestrator
```

---

## Service Logs

```bash
# Bot logs
docker logs -f vh2-deployment-bot-service

# Orchestrator
docker logs -f vh2-orchestrator

# RBAC
docker logs -f vh2-rbac

# Database
docker logs -f vh2-postgres
```

---

## Troubleshooting

### Docker not installed
```bash
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh
```

### Permission denied
```bash
sudo usermod -aG docker $USER && newgrp docker
```

### Services won't start
```bash
docker logs -f vh2-deployment-bot-service
docker-compose -f docker-compose.prod.yaml logs
```

### View database
```bash
docker exec -it vh2-postgres psql -U postgres -d mcp_db
```

### Clean redeploy
```bash
docker-compose -f docker-compose.prod.yaml -p vh2-stack down -v
./scripts/deploy-bot.sh
```

---

## Key Files

| File | Purpose |
|------|---------|
| `scripts/deploy-bot.sh` | Deployment orchestrator |
| `deployment_bot.py` | Microservice agent |
| `docker-compose.prod.yaml` | Stack configuration |
| `Dockerfile.bot` | Bot container image |
| `.env.prod` | Production secrets |

---

## Ports

| Service | Port | URL |
|---------|------|-----|
| Orchestrator | 8000 | http://localhost:8000 |
| RBAC | 8001 | http://localhost:8001 |
| PostgreSQL | 5432 | localhost:5432 |

---

## Volumes

| Volume | Mount | Purpose |
|--------|-------|---------|
| `postgres_data` | `/var/lib/postgresql/data` | Database |
| `deployment_bot_logs` | `/var/log/deployment_bot` | Bot logs |
| `logs/` (host) | Mounted to services | App logs |

---

## Health Checks

Services automatically restart on failure:

- ✓ PostgreSQL: `pg_isready`
- ✓ Orchestrator: `curl /health`
- ✓ RBAC: `curl /health`
- ✓ Bot: Container status

---

## Documentation

- `DEPLOY.md` – Full deployment guide (this file's expanded version)
- `DEPLOYMENT_BOT.md` – Complete bot reference
- `DEPLOYMENT_BOT_INTEGRATION.md` – Integration guide
- `scripts/README.md` – Scripts directory docs

---

## Status Check Workflow

```bash
# 1. Check all services running
docker ps --filter "label=com.docker.compose.project=vh2-stack"

# 2. Verify database
docker exec vh2-postgres pg_isready -U postgres

# 3. Test orchestrator health
curl http://localhost:8000/health

# 4. Test RBAC health
curl http://localhost:8001/health

# 5. Check bot is monitoring
docker logs -f vh2-deployment-bot-service | head -20
```

---

## Environment Variables

### Required (.env.prod)
```env
DB_PASSWORD=              # PostgreSQL password
RBAC_SECRET=              # RBAC service secret
```

### Optional
```env
DB_USER=postgres          # Default: postgres
DB_NAME=mcp_db            # Default: mcp_db
LLM_MODEL=gpt-4o-mini     # Default: gpt-4o-mini
LOG_LEVEL=INFO            # Default: INFO
HEALTH_CHECK_INTERVAL=30  # Default: 30 seconds
RECOVERY_ATTEMPTS=3       # Default: 3 attempts
RECOVERY_DELAY=10         # Default: 10 seconds
```

---

## Security Quick Tips

```bash
# Secure .env.prod
chmod 600 .env.prod

# Generate secure password
openssl rand -base64 32

# View logs securely
sudo tail -f /var/log/deployment_bot/deployment_bot.log

# Rotate secrets monthly
# Edit .env.prod and restart:
docker-compose -f docker-compose.prod.yaml -p vh2-stack restart
```

---

**Ready to deploy? Run:** `./scripts/deploy-bot.sh` ✓
