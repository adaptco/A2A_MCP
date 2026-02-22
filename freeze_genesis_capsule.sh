#!/usr/bin/env bash
# freeze_genesis_capsule.sh — Canonicalize, hash, seal, and ledger the OS genesis capsule
set -euo pipefail

IN="${1:-capsule.os.genesis.v1.json}"
SEALED_BY="${2:-Council}"
OUT_DIR="${OUT:-.out}"
LEDGER_PATH="${OUT_DIR}/scrollstream_ledger.jsonl"

mkdir -p "${OUT_DIR}"

if [[ ! -f "$IN" ]]; then
  echo "Capsule definition not found: $IN" >&2
  exit 1
fi

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
BASE="$(basename "$IN")"
NAME="${BASE%.json}"
CANON="${OUT_DIR}/${NAME}.canon.json"
FROZEN="${OUT_DIR}/${NAME}.frozen.json"

# 1. Canonical body-only (strip attestation, set status to SEALED) and stable sort keys
jq 'del(.attestation) | .status = "SEALED"' "$IN" | jq -cS . > "$CANON"

# 2. Compute digest over canonical body
DIGEST="sha256:$(sha256sum "$CANON" | awk '{print $1}')"

# 3. Embed seal metadata back into capsule
jq -S --arg ts "$TS" --arg by "$SEALED_BY" --arg dig "$DIGEST" '
  .status = "SEALED" |
  .attestation = (
    .attestation // {} |
    . + {
      status: "SEALED",
      sealed_at: $ts,
      sealed_by: $by,
      content_hash: $dig
    }
  )
' "$IN" > "$FROZEN"

# 4. Append ledger events (create ledger file if absent)
if [[ ! -f "$LEDGER_PATH" ]]; then
  touch "$LEDGER_PATH"
fi
{
  printf '{"t":"%s","event":"capsule.seal.v1","capsule":"%s","digest":"%s","sealed_by":"%s"}\n' "$TS" "$NAME" "$DIGEST" "$SEALED_BY"
  printf '{"t":"%s","event":"system.genesis.launch.v1","capsule":"%s","status":"frozen","digest":"%s"}\n' "$TS" "$NAME" "$DIGEST"
} >> "$LEDGER_PATH"

# 5. Optionally register capsule in runtime registry if available
REGISTRY="capsules/runtime/capsule.registry.runtime.v1.json"
if [[ -f "$REGISTRY" ]]; then
  TMP="$(mktemp)"
  jq -S --arg id "$NAME" --arg digest "$DIGEST" '
    .capsules[$id] = (.capsules[$id] // {}) + {
      state: "FROZEN",
      merkle: (.capsules[$id].merkle // "TO_COMPUTE"),
      replay: (.capsules[$id].replay // "replay:os.genesis:20250925:000"),
      digest: $digest
    }
  ' "$REGISTRY" > "$TMP" && mv "$TMP" "$REGISTRY"
fi

echo "✅ SEALED  → $FROZEN"
echo "🔑 DIGEST  → $DIGEST"
echo "🧾 LEDGER  → $LEDGER_PATH"
echo "📄 CANON   → $CANON"
