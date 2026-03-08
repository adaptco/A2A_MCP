# Middleware Runtime Environment (Release Candidate)

This guide bootstraps a release runtime for the A2A middleware stack with:

- PostgreSQL persistence
- FastAPI middleware ingress (`orchestrator.webhook:app`)
- MCP server runtime (`mcp_server.py`)

## 1) Prepare environment

```bash
cp .env.release.example .env.release
```

Update credentials and ports in `.env.release` for your environment.

`MCP_API_TIMEOUT_SECONDS` controls timeout for MCP -> middleware API calls.

## 2) Build and start

```bash
docker compose --env-file .env.release -f docker-compose.release.yml up -d --build
```

## 3) Validate runtime health

```bash
# API docs should return HTTP 200
curl -fsS http://localhost:${MCP_API_PORT:-8000}/healthz > /dev/null && echo "API healthy"

# Services and health checks
docker compose --env-file .env.release -f docker-compose.release.yml ps
```

## 4) Shutdown

```bash
docker compose --env-file .env.release -f docker-compose.release.yml down
```

## Notes for final release hardening

- Move DB credentials to a secrets manager (Vault/Secret Manager/K8s secrets).
- Replace default password and set a private network policy.
- Add TLS termination for public ingress.
- Add log shipping and metrics scraping for production observability.
