# Docker Deployment Guide

This service runs a Gunicorn/Uvicorn ASGI app on port `8000` from the root `Dockerfile`.

## 1) Build image

```bash
docker build -t core-orchestrator:latest .
```

## 2) Run container

```bash
docker run --rm \
  --name core-orchestrator \
  -p 8000:8000 \
  --env-file .env \
  core-orchestrator:latest
```

## 3) Health check

```bash
curl -fsS http://localhost:8000/health || true
```

## Local quick deploy scripts

- Linux/macOS: `./scripts/deploy_local_docker.sh`
- Windows PowerShell: `./scripts/deploy_local_docker.ps1`

## Compose-based production defaults

Use the production override profile:

```bash
docker compose -f docker-compose.prod.yaml up -d --build
```

## Notes

- The container runs as non-root user `appuser` (uid `5678`).
- Keep secrets in `.env`, never in committed files.
- For reproducibility, pin and review `requirements.txt` updates before rebuilding production images.


## Release readiness checks

```bash
./scripts/check_release_readiness.sh
```

This script verifies deployment artifacts are present, Bash script syntax is valid, `docker-compose.prod.yaml` is structurally correct, Dockerfile runs as non-root, and patch formatting is clean.
