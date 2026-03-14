# Deployment Setup Summary

This repository now includes a compact Docker deployment bundle for quick local runs and production compose overrides.

## Added assets

- `docs/DOCKER_DEPLOYMENT.md`: build/run guide and compose usage.
- `scripts/deploy_local_docker.sh`: one-command Linux/macOS local deployment.
- `scripts/deploy_local_docker.ps1`: one-command Windows PowerShell local deployment.
- `docker-compose.prod.yaml`: production-oriented compose overrides.
- `scripts/check_release_readiness.sh`: release-readiness validation checks for deployment assets.

## Usage quickstart

```bash
cp .env.example .env
./scripts/deploy_local_docker.sh
```

Or on Windows:

```powershell
Copy-Item .env.example .env
./scripts/deploy_local_docker.ps1
```


## Release readiness

```bash
./scripts/check_release_readiness.sh
```
