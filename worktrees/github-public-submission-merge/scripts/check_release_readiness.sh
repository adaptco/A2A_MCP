#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

echo "[1/5] Checking required deployment files"
required_files=(
  "Dockerfile"
  ".env.example"
  "docker-compose.prod.yaml"
  "docs/DOCKER_DEPLOYMENT.md"
  "scripts/deploy_local_docker.sh"
  "scripts/deploy_local_docker.ps1"
)
for file in "${required_files[@]}"; do
  [[ -f "${file}" ]] || { echo "Missing required file: ${file}" >&2; exit 1; }
done

echo "[2/5] Validating Bash deploy script syntax"
bash -n scripts/deploy_local_docker.sh

echo "[3/5] Validating production compose YAML structure"
python - <<'PY'
from pathlib import Path
import yaml

payload = yaml.safe_load(Path("docker-compose.prod.yaml").read_text(encoding="utf-8"))
services = payload.get("services", {})
required = {"db", "orchestrator", "rbac", "deployment-bot"}
missing = sorted(required.difference(services))
if missing:
    raise SystemExit(f"Missing required services in docker-compose.prod.yaml: {missing}")
print("compose-services-ok")
PY

echo "[4/5] Verifying Dockerfile contains non-root runtime"
if ! grep -q '^USER appuser$' Dockerfile; then
  echo "Dockerfile must run as non-root appuser" >&2
  exit 1
fi

echo "[5/5] Checking repo diff formatting"
git diff --check

echo "release-readiness-checks-passed"
