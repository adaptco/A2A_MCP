# Deployment Bot Integration Guide

## Overview

Your VH2 Deployment Bot microservice is now ready. This guide shows how to integrate it into your Linux VM deployment workflow.

## Files Created

| File | Size | Purpose |
|------|------|---------|
| `deployment_bot.py` | 10.9 KB | Core microservice agent (build, deploy, monitor, recover) |
| `Dockerfile.bot` | 1.5 KB | Container image for the bot |
| `docker-compose.prod.yaml` | 2.7 KB | Production stack with all services + bot |
| `deploy-bot.sh` | 5.1 KB | Automated deployment script (Linux/Mac) |
| `.env.prod.example` | 552 B | Environment variable template |
| `DEPLOYMENT_BOT.md` | 6.6 KB | Full documentation |

## Quick Start (Linux VM)

### Step 1: Copy Files to VM

```bash
# On your VM, navigate to project root
cd /path/to/A2A_MCP

# Copy files (if not already there)
# deployment_bot.py, Dockerfile.bot, docker-compose.prod.yaml, deploy-bot.sh
```

### Step 2: Setup Environment

```bash
# Copy and customize environment file
cp .env.prod.example .env.prod

# Edit with your production secrets
nano .env.prod
# Set secure passwords for DB, RBAC, LLM keys
```

### Step 3: Deploy

```bash
# Make script executable
chmod +x deploy-bot.sh

# Run deployment (handles everything)
./deploy-bot.sh
```

### Step 4: Monitor

```bash
# Watch bot logs
docker logs -f vh2-deployment-bot-service

# Check service status
docker-compose -f docker-compose.prod.yaml -p vh2-stack ps
```

## What Happens During Deployment

```
deploy-bot.sh
  ├─ 1. Verify prerequisites (docker, docker-compose)
  ├─ 2. Load .env.prod configuration
  ├─ 3. Create log directories
  ├─ 4. Build deployment bot image (Dockerfile.bot)
  ├─ 5. Deploy full stack (docker-compose.prod.yaml)
  │   ├─ PostgreSQL (with health checks)
  │   ├─ Orchestrator (with health checks)
  │   ├─ RBAC (with health checks)
  │   └─ Deployment Bot (with monitoring)
  └─ 6. Display status and show next steps
```

## Bot Capabilities

### 1. Building Images
```bash
python deployment_bot.py build
```
- Compiles all Dockerfiles
- Tags images as `vh2-*:latest`
- Outputs build logs to `logs/`

### 2. Deploying Stack
```bash
python deployment_bot.py deploy
```
- Starts all services via docker-compose
- Waits for health checks to pass
- Verifies all containers are running

### 3. Continuous Monitoring
```bash
python deployment_bot.py monitor --interval 30
```
- Polls service health every 30 seconds
- Logs snapshots to `health_snapshots.jsonl`
- Detects unhealthy services immediately

### 4. Auto-Recovery
When a service fails:
- Logs the failure
- Attempts restart (configurable retries)
- Waits between attempts (configurable delay)
- Logs recovery success/failure

### 5. Status Checks
```bash
python deployment_bot.py status
```
Shows real-time status of all containers.

## Monitoring & Logging

### Log Locations

Inside the container:
```
/var/log/deployment_bot/
  ├─ deployment_bot.log          # Main bot logs
  ├─ build.log                   # Image build output
  ├─ deploy.log                  # Stack deployment output
  ├─ health_snapshots.jsonl      # Health history (JSON Lines)
  └─ *.log                        # Error logs
```

Outside the container:
```bash
logs/
  ├─ orchestrator/
  ├─ rbac/
  └─ deployment_bot/
```

### Viewing Logs

Real-time bot logs:
```bash
docker logs -f vh2-deployment-bot-service
```

Service-specific logs:
```bash
docker logs -f vh2-orchestrator
docker logs -f vh2-rbac
docker logs -f vh2-postgres
```

Health check history:
```bash
docker exec vh2-deployment-bot-service tail -f /var/log/deployment_bot/health_snapshots.jsonl
```

## Configuration Reference

### Environment Variables (.env.prod)

```bash
# Database
DB_USER=postgres
DB_PASSWORD=your-secure-password
DB_NAME=mcp_db

# LLM Model
LLM_MODEL=gpt-4o-mini
A2A_ORCHESTRATION_MODEL=
A2A_ORCHESTRATION_EMBEDDING_LANGUAGE=code

# RBAC
RBAC_SECRET=your-rbac-secret

# Bot Configuration
HEALTH_CHECK_INTERVAL=30          # How often to check health (seconds)
RECOVERY_ATTEMPTS=3                # How many times to retry restart
RECOVERY_DELAY=10                  # Delay between retries (seconds)
```

### Docker Compose Overrides

Edit `docker-compose.prod.yaml` to:
- Change port mappings
- Add resource limits (memory, CPU)
- Customize health check thresholds
- Add additional services
- Configure volumes and mounts

## Architecture Diagram

```
Host Linux VM
├─ Docker Engine
│  ├─ Network: vh2-network
│  ├─ Container: postgres:15
│  │  ├─ Health: pg_isready
│  │  └─ Volume: postgres_data
│  ├─ Container: orchestrator
│  │  ├─ Health: curl localhost:8000/health
│  │  └─ Depends: postgres
│  ├─ Container: rbac
│  │  ├─ Health: curl localhost:8001/health
│  │  └─ Port: 8001
│  └─ Container: deployment-bot
│     ├─ Role: Monitor & Recover
│     ├─ Mounts: /var/run/docker.sock
│     └─ Logs: /var/log/deployment_bot
└─ Volumes
   ├─ postgres_data (persisted)
   ├─ deployment_bot_logs (persisted)
   └─ logs/ (host-side, mounted)
```

## Troubleshooting

### Issue: "Docker is not installed"
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
docker-compose --version  # Verify
```

### Issue: "Permission denied" on docker.sock
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Restart docker
sudo systemctl restart docker
# Verify
docker ps
```

### Issue: Services won't start
```bash
# Check bot logs
docker logs -f vh2-deployment-bot-service

# Check specific service
docker logs vh2-orchestrator

# View docker-compose errors
docker-compose -f docker-compose.prod.yaml logs
```

### Issue: Auto-recovery keeps restarting services
```bash
# Check if service is crashing
docker logs --tail 50 vh2-orchestrator

# Increase recovery delay to let service stabilize
RECOVERY_DELAY=20 docker-compose -f docker-compose.prod.yaml up -d

# Or disable auto-recovery
ACTION=monitor docker-compose -f docker-compose.prod.yaml up -d deployment-bot
```

## Performance Tuning

### Reduce CPU Usage
Edit `docker-compose.prod.yaml`:
```yaml
orchestrator:
  deploy:
    resources:
      limits:
        cpus: '1'
        memory: 512M
```

### Increase Memory
```yaml
services:
  orchestrator:
    deploy:
      resources:
        limits:
          memory: 2G
```

### Adjust Health Check Frequency
Increase for less frequent checks (reduce CPU):
```bash
HEALTH_CHECK_INTERVAL=60 docker-compose -f docker-compose.prod.yaml up -d
```

## Security Best Practices

1. **Protect .env.prod**
   ```bash
   chmod 600 .env.prod
   ```

2. **Use strong passwords**
   ```bash
   openssl rand -base64 32  # Generate secure password
   ```

3. **Rotate secrets regularly**
   - Change DB_PASSWORD monthly
   - Rotate RBAC_SECRET quarterly
   - Update LLM API keys as needed

4. **Enable log rotation**
   ```bash
   sudo tee /etc/logrotate.d/deployment-bot > /dev/null << 'EOF'
   /var/log/deployment_bot/*.log {
       daily
       rotate 7
       compress
       delaycompress
       notifempty
       create 0600 bot bot
   }
   EOF
   ```

5. **Monitor resource usage**
   ```bash
   docker stats vh2-deployment-bot-service
   ```

## Next Steps

1. **Test on Dev VM** – Run deploy-bot.sh on a test VM first
2. **Configure Monitoring** – Set up Datadog/New Relic alerts
3. **Document Runbooks** – Create incident response procedures
4. **Schedule Backups** – Configure postgres backup cron jobs
5. **Plan Maintenance** – Schedule service updates

## Support & Documentation

- Full docs: `DEPLOYMENT_BOT.md`
- Code comments: `deployment_bot.py`
- Docker reference: https://docs.docker.com
- Compose reference: https://docs.docker.com/compose/

## Version Info

- deployment_bot.py: v1.0.0
- Dockerfile.bot: Ubuntu 22.04 LTS
- Python: 3.11-slim
- Docker Compose: v3.9
- Status: Production Ready ✓

Let me know if you have any questions!
