#!/usr/bin/env bash
# adjudicate_ledger.sh — normalize scrollstream_ledger.jsonl for Qube domain
set -euo pipefail

IN="${1:-.out/scrollstream_ledger.jsonl}"
OUT="${2:-.out/scrollstream_ledger.normalized.jsonl}"
AUDIT="${3:-.out/resolver.audit.jsonl}"

# enrich with idempotency key (event + capsule + digest)
with_keys=$(mktemp)
jq -c '
  . as $e |
  .key = (
    ( .event // "" )
    + ":" + ( .capsule // .capsule_id // "" )
    + ":" + ( .digest // "" )
  )
' "$IN" > "$with_keys"

# keep earliest occurrence of each key
unique=$(mktemp)
jq -s '
  sort_by(.t // "") |
  unique_by(.key) |
  map(del(.key))
' "$with_keys" > "$unique"

jq -c '.[]' "$unique" > "$OUT"

# derive Qube-only stream (capsule/render/registry/qlock prefixes)
jq -c '
  select((.event|tostring) as $ev |
    ($ev|startswith("capsule.")) or ($ev|startswith("render.")) or ($ev|startswith("registry.")) or ($ev|startswith("qlock.")))
' "$OUT" > "${OUT%.jsonl}.qube.jsonl"

# capture cultural / off-domain events into audit lane
if [[ -s "$AUDIT" ]]; then
  cp "$AUDIT" "${AUDIT}.bak"
fi
jq -c 'select((.event|tostring|startswith("cultural.")))' "$IN" >> "$AUDIT"

echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"event\":\"ledger.normalize.v1\",\"input\":\"$IN\",\"output\":\"$OUT\"}" >> "$AUDIT"

echo "✅ Ledger normalized → $OUT"
