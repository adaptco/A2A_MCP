# 🚀 VH2 Deployment Bot - Execution Guide

## Quick Start (One Command)

From project root on Linux VM:

```bash
# Make script executable
chmod +x scripts/deploy-bot.sh

# Run deployment
./scripts/deploy-bot.sh
```

Done! The bot will:
1. Verify Docker is installed and running
2. Load production configuration from `.env.prod`
3. Build the deployment bot Docker image
4. Deploy the full VH2 stack (4 containers)
5. Wait for services to start
6. Display status
7. Start continuous monitoring

---

## Prerequisites

Your Linux VM needs:
- ✓ Docker installed
- ✓ docker-compose installed
- ✓ Bash shell
- ✓ Write permissions to project directory

Check prerequisites:
```bash
docker --version          # Should be 20.10+
docker-compose --version  # Should be 2.0+
which bash                # Should find /bin/bash
```

---

## Configuration (Required)

Before running deployment, create `.env.prod`:

```bash
# Copy template
cp .env.prod.example .env.prod

# Edit with your production secrets
nano .env.prod
chmod 600 .env.prod
```

Minimal configuration:
```env
DB_PASSWORD=your-secure-password
RBAC_SECRET=your-rbac-secret
```

---

## Deployment Steps

### Step 1: Prepare
```bash
# Navigate to project root
cd /path/to/A2A_MCP

# Create environment file
cp .env.prod.example .env.prod
nano .env.prod  # Set secure passwords
chmod 600 .env.prod

# Make script executable
chmod +x scripts/deploy-bot.sh
```

### Step 2: Deploy
```bash
./scripts/deploy-bot.sh
```

Expected output:
```
[INFO] =========================================
[INFO] VH2 Deployment Bot - Automated Deploy
[INFO] =========================================
[INFO] Project root: /path/to/A2A_MCP
[INFO] Checking prerequisites...
[✓] Docker found: Docker version 24.0.0
[✓] docker-compose found: Docker Compose version v2.20.0
[✓] Docker daemon is running
[✓] Compose file found: /path/to/A2A_MCP/docker-compose.prod.yaml
[INFO] Loading environment from: /path/to/A2A_MCP/.env.prod
[✓] Environment loaded
[INFO] Creating log directories...
[✓] Log directories created
[INFO] Building deployment bot image...
[✓] Bot image built: vh2-deployment-bot:latest
[INFO] Deploying full stack with docker-compose...
[✓] Stack deployed successfully
[INFO] Waiting for services to start...
[✓] All services are running
[INFO] === SERVICE STATUS ===
CONTAINER ID   IMAGE                                STATUS
abc123...      vh2-postgres:latest                  Up 5s
def456...      vh2-orchestrator:latest              Up 3s
ghi789...      vh2-rbac:latest                      Up 2s
jkl012...      vh2-deployment-bot:latest            Up 1s
[INFO] ======================
[✓] Deployment Bot is ready!
[INFO] 
[INFO] Next steps:
[INFO] 1. Check bot status:  docker logs -f vh2-deployment-bot-service
[INFO] 2. View stack:        docker-compose -f docker-compose.prod.yaml -p vh2-stack ps
[INFO] 3. Check logs:        tail -f logs/**/*.log
[INFO] Deployment complete!
[✓] Deployment bot is running
```

### Step 3: Monitor
```bash
# Real-time bot logs
docker logs -f vh2-deployment-bot-service

# Or check health history
docker exec vh2-deployment-bot-service \
  tail -f /var/log/deployment_bot/health_snapshots.jsonl | jq .
```

---

## Service Status

After deployment, check services:

```bash
# All services
docker-compose -f docker-compose.prod.yaml -p vh2-stack ps

# Specific service logs
docker logs -f vh2-orchestrator
docker logs -f vh2-rbac
docker logs -f vh2-postgres

# Bot monitoring
docker logs -f vh2-deployment-bot-service
```

---

## What Gets Deployed

### 4 Containers

| Container | Port | Role | Health Check |
|-----------|------|------|--------------|
| vh2-postgres | 5432 | Database | `pg_isready` |
| vh2-orchestrator | 8000 | Orchestration API | `curl /health` |
| vh2-rbac | 8001 | RBAC Service | `curl /health` |
| vh2-deployment-bot | - | Monitor & Recovery | Container status |

### Volumes (Persisted)

- `postgres_data` → PostgreSQL data
- `deployment_bot_logs` → Bot logs & health history
- `logs/` → Application logs

### Network

- `vh2-network` → Internal bridge network for service communication

---

## Log Locations

Inside containers:
```
/var/log/deployment_bot/
  ├─ deployment_bot.log          # Main bot activity
  ├─ build.log                   # Image build output
  ├─ deploy.log                  # Stack deployment output
  ├─ health_snapshots.jsonl      # Health check history (JSON Lines)
  └─ *.log                        # Error logs
```

On host:
```
logs/
  ├─ orchestrator/
  ├─ rbac/
  └─ deployment_bot/
```

---

## Monitoring Commands

### Real-time bot logs
```bash
docker logs -f vh2-deployment-bot-service
```

### Service-specific logs
```bash
docker logs -f vh2-orchestrator   # Orchestrator logs
docker logs -f vh2-rbac           # RBAC logs
docker logs -f vh2-postgres       # Database logs
```

### Health history (last 50 entries)
```bash
docker exec vh2-deployment-bot-service \
  tail -50 /var/log/deployment_bot/health_snapshots.jsonl | jq .
```

### Service metrics
```bash
docker stats --no-stream
```

---

## Recovery & Troubleshooting

### If a service fails

The bot automatically detects failures and attempts recovery:

```bash
# View recovery attempts
docker logs -f vh2-deployment-bot-service | grep -i "recovery"

# Manually recover a service
python deployment_bot.py recover --service orchestrator

# Check service status
python deployment_bot.py status
```

### If deployment fails

Check logs:
```bash
# Bot logs
docker logs -f vh2-deployment-bot-service

# Compose logs
docker-compose -f docker-compose.prod.yaml logs

# System issues
docker system df          # Disk usage
docker system prune -a    # Clean up unused resources
```

### Common issues

**"Docker is not installed"**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

**"Permission denied"**
```bash
sudo usermod -aG docker $USER
newgrp docker
docker ps  # Test
```

**"Services won't start"**
```bash
# Check individual service logs
docker logs vh2-orchestrator
docker logs vh2-postgres

# Check resource constraints
docker system df
```

---

## Configuration Tuning

### Health check frequency
Default: 30 seconds

```bash
HEALTH_CHECK_INTERVAL=60 docker-compose -f docker-compose.prod.yaml up -d
```

### Recovery attempts
Default: 3 retries

```bash
RECOVERY_ATTEMPTS=5 docker-compose -f docker-compose.prod.yaml up -d
```

### Recovery delay
Default: 10 seconds between retries

```bash
RECOVERY_DELAY=20 docker-compose -f docker-compose.prod.yaml up -d
```

---

## Advanced Operations

### Stop all services
```bash
docker-compose -f docker-compose.prod.yaml -p vh2-stack down
```

### Stop specific service
```bash
docker-compose -f docker-compose.prod.yaml -p vh2-stack stop orchestrator
```

### View database
```bash
docker exec -it vh2-postgres psql -U postgres -d mcp_db
```

### Rebuild images
```bash
python deployment_bot.py build
```

### Full redeploy (clean)
```bash
# Stop and remove everything
docker-compose -f docker-compose.prod.yaml -p vh2-stack down -v

# Rebuild and redeploy
./scripts/deploy-bot.sh
```

---

## Verification Checklist

After deployment, verify:

- [ ] All 4 services running: `docker ps --filter "label=com.docker.compose.project=vh2-stack"`
- [ ] Database responding: `docker exec vh2-postgres pg_isready -U postgres`
- [ ] Orchestrator health: `curl http://localhost:8000/health`
- [ ] RBAC health: `curl http://localhost:8001/health`
- [ ] Bot monitoring: `docker logs -f vh2-deployment-bot-service`
- [ ] Logs created: `ls -la logs/`

---

## Security Checklist

- [ ] `.env.prod` permissions: `chmod 600 .env.prod`
- [ ] Secure passwords in `.env.prod`: Use `openssl rand -base64 32`
- [ ] Docker group membership: User in docker group
- [ ] Network isolation: Services on `vh2-network`
- [ ] Log rotation configured: For `/var/log/deployment_bot/`
- [ ] Firewall rules: Only needed ports exposed

---

## Production Deployment

For production:

1. Use strong, unique passwords in `.env.prod`
2. Configure log rotation
3. Set up monitoring/alerting for container failures
4. Configure PostgreSQL backups
5. Enable resource limits in docker-compose
6. Use external log aggregation (ELK, Datadog, etc.)
7. Document runbooks for common incidents
8. Test disaster recovery procedures

---

## Support & Documentation

Full docs available:
- `DEPLOYMENT_BOT.md` – Complete reference
- `DEPLOYMENT_BOT_INTEGRATION.md` – Integration guide
- `DEPLOYMENT_BOT_SETUP.md` – Implementation overview
- `scripts/README.md` – Scripts documentation

---

**Status: ✓ Ready to Deploy**

You can now run `./scripts/deploy-bot.sh` from the project root!
