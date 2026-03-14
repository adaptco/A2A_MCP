#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-core-orchestrator:local}"
CONTAINER_NAME="${CONTAINER_NAME:-core-orchestrator-local}"
PORT="${PORT:-8000}"
ENV_FILE="${ENV_FILE:-.env}"

echo "[1/3] Building ${IMAGE_NAME}"
docker build -t "${IMAGE_NAME}" .

echo "[2/3] Replacing container ${CONTAINER_NAME} (if present)"
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

echo "[3/3] Starting container on port ${PORT}"
docker run -d \
  --name "${CONTAINER_NAME}" \
  -p "${PORT}:8000" \
  --env-file "${ENV_FILE}" \
  --restart unless-stopped \
  "${IMAGE_NAME}"

echo "Container started: ${CONTAINER_NAME}"
echo "Logs: docker logs -f ${CONTAINER_NAME}"
