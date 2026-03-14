#!/usr/bin/env bash
# Dual freeze ritual for CiCi's rehearsal + Git governance capsules
# Usage: ./freeze_dual_capsules.sh <capsule1.json> <capsule2.json> <ledger.ndjson>

set -euo pipefail

CAP1="${1:?First capsule required}"
CAP2="${2:?Second capsule required}"
LEDGER="${3:?Ledger file required}"

ts(){ date -u +%Y-%m-%dT%H:%M:%SZ; }

freeze_capsule() {
  local CAP="$1"
  local NAME="$(basename "$CAP" .json)"
  local CANON
  CANON="$(mktemp)"
  jq -S 'del(.attestation,.seal,.signatures)' "$CAP" > "$CANON"
  local DIGEST
  DIGEST="sha256:$(sha256sum "$CANON" | awk '{print $1}')"
  local STAMP
  STAMP="$(ts)"
  local SEALED
  SEALED=".out/${NAME}.sealed.json"
  mkdir -p .out
  jq -S --arg h "$DIGEST" --arg ts "$STAMP" '
    .attestation = {
      status: "SEALED",
      sealed_by: "Council",
      sealed_at: $ts,
      content_hash: $h
    } | .status = "SEALED"
  ' "$CAP" > "$SEALED"

  {
    echo "{\"t\":\"$STAMP\",\"event\":\"capsule.commit.v1\",\"capsule\":\"$NAME\",\"digest\":\"$DIGEST\"}"
    echo "{\"t\":\"$STAMP\",\"event\":\"capsule.review.v1\",\"capsule\":\"$NAME\",\"digest\":\"$DIGEST\",\"reviewer\":\"Council\"}"
    echo "{\"t\":\"$STAMP\",\"event\":\"capsule.seal.v1\",\"capsule\":\"$NAME\",\"digest\":\"$DIGEST\",\"sealed_by\":\"Council\"}"
  } >> "$LEDGER"

  echo "✅ Capsule sealed -> $SEALED"
  echo "   -> Digest: $DIGEST"
}

echo "🔒 Beginning dual freeze ritual..."
freeze_capsule "$CAP1"
freeze_capsule "$CAP2"
echo "📜 Dual freeze complete. Ledger updated -> $LEDGER"
