# Deployment Scripts

Automation scripts for VH2 system deployment and management.

## Deploy Bot

The Deployment Bot microservice automates building, deploying, monitoring, and recovering the VH2 stack.

### Quick Start

From project root:

```bash
# Bash/Linux/Mac
chmod +x scripts/deploy-bot.sh
./scripts/deploy-bot.sh

# Or via Python wrapper (all platforms)
python scripts/deploy_bot_wrapper.py
```

### What It Does

1. ✓ Verifies Docker prerequisites
2. ✓ Loads `.env.prod` configuration
3. ✓ Creates log directories
4. ✓ Builds deployment bot Docker image
5. ✓ Deploys full VH2 stack (PostgreSQL, Orchestrator, RBAC, Bot)
6. ✓ Waits for services to start
7. ✓ Displays service status
8. ✓ Starts continuous monitoring

### Configuration

Create `.env.prod` in project root (template: `.env.prod.example`):

```env
DB_PASSWORD=your-secure-password
RBAC_SECRET=your-rbac-secret
LLM_MODEL=gpt-4o-mini
HEALTH_CHECK_INTERVAL=30
RECOVERY_ATTEMPTS=3
RECOVERY_DELAY=10
```

### Monitoring

After deployment, monitor the bot:

```bash
# Real-time logs
docker logs -f vh2-deployment-bot-service

# Service status
docker-compose -f docker-compose.prod.yaml -p vh2-stack ps

# Health history
docker exec vh2-deployment-bot-service tail -f /var/log/deployment_bot/health_snapshots.jsonl
```

### Direct Bot Commands

For advanced usage, call the bot directly:

```bash
# Full deployment (build + deploy + monitor)
python deployment_bot.py full-deploy

# Build images only
python deployment_bot.py build

# Deploy stack only
python deployment_bot.py deploy

# Start monitoring
python deployment_bot.py monitor --interval 30

# Check current status
python deployment_bot.py status

# Recover specific service
python deployment_bot.py recover --service orchestrator
```

## Other Scripts

- `automate_healing.py` – Service healing automation
<<<<<<< HEAD
=======
- `automation_runtime.ps1` – Bring up the simulator/runtime automation environment
>>>>>>> origin/main
- `build_multimodal_rag_bundle.py` – RAG bundle builder
- `build_worldline_block.py` – World line block builder
- `cleanup_repo.py` – Repository cleanup
- `configure_twilio_agent.py` – Twilio agent setup
- `inspect_db.py` – Database inspection
- `knowledge_ingestion.py` – Knowledge ingestion
- `oidc_token.py` – OIDC token management
- `send_channel_message.py` – Channel messaging
- `tune_avatar_style.py` – Avatar styling
- `unified_runtime.ps1` – Unified runtime (PowerShell)
- `pre_pr_check.ps1` – Pre-PR validation (PowerShell)

## Documentation

- `deployment_bot.py` – Microservice agent (main implementation)
- `DEPLOYMENT_BOT.md` – Complete bot documentation
- `DEPLOYMENT_BOT_INTEGRATION.md` – Integration guide
- `DEPLOYMENT_BOT_SETUP.md` – Setup summary

## Troubleshooting

### Docker not found
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Services won't start
```bash
# Check bot logs
docker logs -f vh2-deployment-bot-service

# Check specific service
docker logs vh2-orchestrator

# View docker-compose errors
docker-compose -f docker-compose.prod.yaml logs
```

### Permission denied
```bash
# Fix docker socket permissions
sudo usermod -aG docker $USER
sudo systemctl restart docker

# Or for Mac/Docker Desktop
# Restart Docker Desktop app
```

## Environment Setup

1. **Create .env.prod:**
   ```bash
   cp .env.prod.example .env.prod
   nano .env.prod  # Edit with your secrets
   chmod 600 .env.prod
   ```

2. **Make scripts executable:**
   ```bash
   chmod +x scripts/deploy-bot.sh
   ```

3. **Verify prerequisites:**
   ```bash
   docker --version
   docker-compose --version
   ```

## Security

- Keep `.env.prod` file permissions restricted: `chmod 600 .env.prod`
- Use strong passwords (generate with `openssl rand -base64 32`)
- Never commit `.env.prod` to version control (use `.env.prod.example` as template)
- Rotate secrets regularly (monthly for DB, quarterly for RBAC)

## Support

For detailed information:
- Full documentation: `DEPLOYMENT_BOT.md`
- Integration guide: `DEPLOYMENT_BOT_INTEGRATION.md`
- Setup summary: `DEPLOYMENT_BOT_SETUP.md`
- Code reference: `deployment_bot.py`

---

**Status: Production Ready ✓**
