#!/usr/bin/env bash
set -euo pipefail
CHANNEL="${1:-production}"

echo "[deploy] channel=$CHANNEL"
echo "[deploy] building…"
# e.g. npm ci && npm run build

if [[ -x ./render ]]; then
  echo "[deploy] running renderer"
  ./render --input dist --out ops/boo/avatar/guard/out || true
fi

echo "[deploy] emitting ledger heartbeat"
mkdir -p storage
echo "{\"type\":\"DEPLOY\",\"channel\":\"$CHANNEL\",\"ts\":\"$(date -Iseconds)\"}" >> storage/ledger.jsonl

echo "[deploy] done"
