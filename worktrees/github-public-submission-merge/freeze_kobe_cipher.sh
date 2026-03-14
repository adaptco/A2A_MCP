#!/usr/bin/env bash
set -euo pipefail
IN="${1:-capsule.kobe.cipher.v1.json}"
OUT="${OUT:-.out}"; mkdir -p "$OUT"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
CANON="$OUT/capsule.kobe.cipher.v1.canon.json"
FROZEN="$OUT/capsule.kobe.cipher.v1.frozen.json"
LEDGER="$OUT/scrollstream_ledger.jsonl"

jq 'del(.attestation) | .status="SEALED"' "$IN" | jq -cS . > "$CANON"
DIG="sha256:$(sha256sum "$CANON" | awk '{print $1}')"
jq -S --arg ts "$TS" --arg dig "$DIG" '
  .attestation = {status:"SEALED", sealed_by:"Council", sealed_at:$ts, content_hash:$dig} |
  .status="SEALED"
' "$IN" > "$FROZEN"

{
  echo "{\"t\":\"$TS\",\"event\":\"capsule.seal.v1\",\"capsule\":\"capsule.kobe.cipher.v1\",\"digest\":\"$DIG\"}"
  echo "{\"t\":\"$TS\",\"event\":\"cultural.cipher.fossilize.v1\",\"subject\":\"Kobe Bryant\",\"digest\":\"$DIG\",\"status\":\"published\"}"
} >> "$LEDGER"

echo "✅ SEALED  → $FROZEN"
echo "🔑 DIGEST  → $DIG"
echo "🧾 LEDGER  → $LEDGER"
echo "📄 CANON   → $CANON"
