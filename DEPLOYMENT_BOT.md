# VH2 Deployment Bot Microservice

A production-ready microservice agent that automates the deployment, monitoring, and recovery of the VH2 system on Linux VMs.

## Features

- **Automated Build**: Builds all Docker images from docker-compose.prod.yaml
- **Stack Deployment**: Deploys the full VH2 stack (DB, Orchestrator, RBAC, Monitoring)
- **Health Monitoring**: Continuous health checks for all services
- **Auto-Recovery**: Automatically restarts unhealthy services with configurable retry logic
- **Comprehensive Logging**: Structured logs for audit and debugging
- **Non-Root Security**: Runs as unprivileged user inside container

## Architecture

```
┌─────────────────────────────────────────────┐
│   Deployment Bot Container                  │
│  ┌───────────────────────────────────────┐  │
│  │ deployment_bot.py                     │  │
│  │  - Build images                       │  │
│  │  - Deploy stack                       │  │
│  │  - Monitor health                     │  │
│  │  - Auto-recover services              │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
         │
         ├─ Manages ─→ PostgreSQL Container
         │
         ├─ Manages ─→ Orchestrator Container
         │
         ├─ Manages ─→ RBAC Container
         │
         └─ Monitors → via Docker API
```

## Quick Start

### Prerequisites

- Linux VM with Docker and docker-compose installed
- Bash shell
- Write permissions to project directory

### Deployment (2 steps)

```bash
# 1. Make script executable
chmod +x deploy-bot.sh

# 2. Run deployment
./deploy-bot.sh
```

The script will:
1. ✓ Verify Docker prerequisites
2. ✓ Load environment configuration
3. ✓ Build deployment bot image
4. ✓ Deploy full stack
5. ✓ Wait for services to start
6. ✓ Display service status
7. ✓ Start continuous monitoring

### Monitoring

**View bot logs in real-time:**
```bash
docker logs -f vh2-deployment-bot-service
```

**Check service status:**
```bash
docker-compose -f docker-compose.prod.yaml -p vh2-stack ps
```

**View all logs:**
```bash
tail -f logs/**/*.log
```

## Configuration

### Environment Variables

Create `.env.prod` in the project root (template: `.env.prod.example`):

```env
# Database
DB_USER=postgres
DB_PASSWORD=secure-password
DB_NAME=mcp_db

# LLM
LLM_MODEL=gpt-4o-mini

# RBAC
RBAC_SECRET=secure-secret

# Bot Configuration
HEALTH_CHECK_INTERVAL=30          # Health checks every 30s
RECOVERY_ATTEMPTS=3                # Restart unhealthy service 3 times
RECOVERY_DELAY=10                  # Wait 10s between recovery attempts
```

### Docker Compose Override

Edit `docker-compose.prod.yaml` to customize:
- Service resource limits
- Port mappings
- Volume mounts
- Health check thresholds
- Restart policies

## Usage

### Via Docker Compose (Recommended)

Full deployment with continuous monitoring:
```bash
docker-compose -f docker-compose.prod.yaml -p vh2-stack up -d
```

### Via deployment_bot.py (Direct)

Install Python 3.11+ and docker-compose, then:

```bash
# Full deployment (build + deploy + monitor)
python deployment_bot.py full-deploy

# Build images only
python deployment_bot.py build

# Deploy stack only
python deployment_bot.py deploy

# Start monitoring loop
python deployment_bot.py monitor --interval 30

# Check current status
python deployment_bot.py status

# Recover specific service
python deployment_bot.py recover --service orchestrator
```

## Monitoring & Recovery

### How Health Checks Work

1. **Polling**: Every 30 seconds (configurable), bot queries container status
2. **Detection**: Identifies services not in "running" state
3. **Recovery**: Attempts to restart with exponential backoff
4. **Logging**: All events logged to `/var/log/deployment_bot/`

### Log Files

- `deploy.log` – Stack deployment output
- `build.log` – Image build logs
- `health_snapshots.jsonl` – Health check history (JSON Lines)
- `deployment_bot.log` – Main bot activity

### Health Check Example

```json
{
  "timestamp": "2025-01-15T10:30:45.123456",
  "health": {
    "db": true,
    "orchestrator": true,
    "rbac": true
  },
  "all_healthy": true
}
```

## Troubleshooting

### Services won't start

1. Check logs:
   ```bash
   docker logs -f vh2-deployment-bot-service
   ```

2. Verify environment:
   ```bash
   cat .env.prod
   ```

3. Check Docker resources:
   ```bash
   docker system df
   ```

### Bot keeps restarting services

1. Check service-specific logs:
   ```bash
   docker logs -f vh2-orchestrator
   ```

2. Increase recovery delay:
   ```bash
   RECOVERY_DELAY=20 docker-compose -f docker-compose.prod.yaml up -d
   ```

3. Disable auto-recovery (set to monitor-only):
   ```bash
   ACTION=monitor docker-compose -f docker-compose.prod.yaml up -d deployment-bot
   ```

### Permission denied errors

Ensure Docker socket has correct permissions:
```bash
ls -l /var/run/docker.sock
# Should be readable by your user or docker group
usermod -aG docker $USER
```

## Security Considerations

- **Non-Root User**: Bot runs as `bot` user (UID 1000) inside container
- **Docker Socket**: Mounted read-only for health checks
- **Secrets Management**: Use `.env.prod` with restrictive file permissions:
  ```bash
  chmod 600 .env.prod
  ```
- **Log Rotation**: Configure logrotate for `/var/log/deployment_bot/`
- **Network Isolation**: Services run in isolated `vh2-network` bridge

## Production Checklist

- [ ] Set secure passwords in `.env.prod`
- [ ] Configure log rotation
- [ ] Set up monitoring/alerting for bot container
- [ ] Test recovery procedures
- [ ] Document service dependencies
- [ ] Configure automated backups for PostgreSQL volume
- [ ] Set resource limits in docker-compose
- [ ] Enable log aggregation (ELK, Datadog, etc.)
- [ ] Test disaster recovery procedures

## Support

For issues or questions:
1. Check logs: `docker logs -f vh2-deployment-bot-service`
2. Review configuration: `cat .env.prod`
3. Verify prerequisites: `docker --version && docker-compose --version`
4. Check Docker daemon: `docker ps`

## License

Part of VH2 system. See LICENSE file.
