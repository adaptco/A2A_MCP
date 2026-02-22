#!/usr/bin/env bash
# freeze_ethereal_wrap.sh  —  Canonicalize → hash (body-only) → seal → ledger
# deps: jq, sha256sum
set -euo pipefail

IN="${1:-capsule.scene.ethereal_wrap.v1.json}"
SEALED_BY="${2:-Council}"
OUT="${OUT:-.out}"; mkdir -p "$OUT"

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
BASE="$(basename "$IN")"
CANON="$OUT/${BASE%.json}.canon.json"      # body-only (no attestation) for digest
FROZEN="$OUT/${BASE%.json}.frozen.json"    # sealed artifact
LEDGER="$OUT/scrollstream_ledger.jsonl"    # append-only ledger

# 1) Canonicalize BODY-ONLY (strip attestation block), stable-sort keys
jq 'del(.attestation) | .status="SEALED"' "$IN" | jq -cS . > "$CANON"

# 2) Compute sha256 over canonical body
DIG="sha256:$(sha256sum "$CANON" | awk "{print \$1}")"

# 3) Embed seal into full capsule
jq -S --arg ts "$TS" --arg by "$SEALED_BY" --arg dig "$DIG" '
  .status = "SEALED" |
  .attestation = (
    .attestation // {} |
    . + {status:"SEALED", sealed_at:$ts, sealed_by:$by, content_hash:$dig}
  )
' "$IN" > "$FROZEN"

# 4) Emit ledger events
{
  echo "{\"t\":\"$TS\",\"event\":\"capsule.seal.v1\",\"capsule\":\"${BASE%.*}\",\"digest\":\"$DIG\",\"sealed_by\":\"$SEALED_BY\"}"
  echo "{\"t\":\"$TS\",\"event\":\"render.fossilize.v1\",\"scene\":\"Ethereal Wrap\",\"capsule\":\"${BASE%.*}\",\"status\":\"published\",\"digest\":\"$DIG\"}"
} >> "$LEDGER"

# 5) (Optional) register into runtime registry if present
REG="capsule.registry.runtime.v1.json"
if [[ -f "$REG" ]]; then
  TMP="$(mktemp)"
  jq -S --arg id "$(jq -r '.capsule_id' "$IN")" --arg dig "$DIG" '
    .capsules[$id] = (.capsules[$id] // {}) + {state:"FROZEN", merkle:"TO_COMPUTE", replay: (.capsules[$id].replay // null)} |
    .attestation = ((.attestation // {}) + {merkle_anchor:true})
  ' "$REG" > "$TMP" && mv "$TMP" "$REG"
fi

echo "✅ SEALED  → $FROZEN"
echo "🔑 DIGEST  → $DIG"
echo "🧾 LEDGER  → $LEDGER"
echo "📄 CANON   → $CANON"
