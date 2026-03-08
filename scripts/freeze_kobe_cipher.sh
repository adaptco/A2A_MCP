#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CAPSULE_PATH="${ROOT_DIR}/capsules/cultural/capsule.kobe.cipher.v1.json"
CANON_SCRIPT="${ROOT_DIR}/scripts/canonicalize_manifest.py"
OUTPUT_DIR="${ROOT_DIR}/runtime"
CANONICAL_PATH="${OUTPUT_DIR}/capsule.kobe.cipher.v1.canonical.json"
FROZEN_PATH="${OUTPUT_DIR}/capsule.kobe.cipher.v1.frozen.json"
HASH_PATH="${OUTPUT_DIR}/capsule.kobe.cipher.v1.sha256"
LEDGER_PATH="${OUTPUT_DIR}/scrollstream_ledger.jsonl"
HUD_PATH="${OUTPUT_DIR}/hud_events.jsonl"

MAKER_SIGNATURE=""
CHECKER_SIGNATURE=""
HUD_EVENT="glyph.pulse"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --maker-signature)
      MAKER_SIGNATURE="${2:-}"
      shift 2
      ;;
    --checker-signature)
      CHECKER_SIGNATURE="${2:-}"
      shift 2
      ;;
    --hud-event)
      HUD_EVENT="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "${MAKER_SIGNATURE}" || -z "${CHECKER_SIGNATURE}" ]]; then
  echo "Both --maker-signature and --checker-signature are required." >&2
  exit 1
fi

if [[ "${MAKER_SIGNATURE}" == "${CHECKER_SIGNATURE}" ]]; then
  echo "Maker and checker signatures must be distinct." >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required but was not found in PATH." >&2
  exit 1
fi

if [[ ! -f "${CAPSULE_PATH}" ]]; then
  echo "Cipher capsule not found at ${CAPSULE_PATH}" >&2
  exit 1
fi

if [[ ! -f "${CANON_SCRIPT}" ]]; then
  echo "Canonicalization script not found at ${CANON_SCRIPT}" >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"

python3 "${CANON_SCRIPT}" < "${CAPSULE_PATH}" > "${CANONICAL_PATH}"
HASH=$(sha256sum "${CANONICAL_PATH}" | cut -d' ' -f1)
DIGEST="sha256:${HASH}"
printf "%s\n" "${DIGEST}" > "${HASH_PATH}"

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

jq -S \
  --arg ts "${TIMESTAMP}" \
  --arg digest "${DIGEST}" \
  --arg maker "${MAKER_SIGNATURE}" \
  --arg checker "${CHECKER_SIGNATURE}" \
  '
    .attestation = (.attestation // {}) |
    .attestation.status = "FOSSILIZED" |
    .attestation.sealed_by = "Council" |
    .attestation.sealed_at = $ts |
    .attestation.content_hash = $digest |
    .attestation.signatures = [$maker, $checker] |
    .status = "SEALED"
  ' "${CAPSULE_PATH}" > "${FROZEN_PATH}"

TEMP_LEDGER=$(mktemp)
export LEDGER_TIMESTAMP="${TIMESTAMP}"
export LEDGER_DIGEST="${DIGEST}"
export LEDGER_MAKER="${MAKER_SIGNATURE}"
export LEDGER_CHECKER="${CHECKER_SIGNATURE}"
export TEMP_LEDGER_PATH="${TEMP_LEDGER}"
python3 - <<'PY'
import json
import os

timestamp = os.environ["LEDGER_TIMESTAMP"]
digest = os.environ["LEDGER_DIGEST"]
maker = os.environ["LEDGER_MAKER"]
checker = os.environ["LEDGER_CHECKER"]
temp_path = os.environ["TEMP_LEDGER_PATH"]

entries = [
    {
        "timestamp": timestamp,
        "event": "capsule.commit.v1",
        "capsule": "capsule.kobe.cipher.v1",
        "digest": digest,
        "maker_signature": maker,
        "sealed_by": "Council"
    },
    {
        "timestamp": timestamp,
        "event": "capsule.review.v1",
        "capsule": "capsule.kobe.cipher.v1",
        "digest": digest,
        "checker_signature": checker,
        "sealed_by": "Council"
    },
    {
        "timestamp": timestamp,
        "event": "capsule.seal.v1",
        "capsule": "capsule.kobe.cipher.v1",
        "digest": digest,
        "signatures": [maker, checker],
        "sealed_by": "Council"
    },
    {
        "timestamp": timestamp,
        "event": "capsule.replay.v1",
        "capsule": "capsule.kobe.cipher.v1",
        "digest": digest,
        "status": "ready"
    },
]

with open(temp_path, "w", encoding="utf-8") as handle:
    for entry in entries:
        json.dump(entry, handle, ensure_ascii=False)
        handle.write("\n")
PY

cat "${TEMP_LEDGER}" >> "${LEDGER_PATH}"
rm -f "${TEMP_LEDGER}"

printf '{"timestamp":"%s","event":"hud.broadcast","capsule":"capsule.kobe.cipher.v1","payload":{"type":"%s","digest":"%s"}}\n' \
  "${TIMESTAMP}" "${HUD_EVENT}" "${DIGEST}" >> "${HUD_PATH}"

printf "Canonical cipher written to %s\n" "${CANONICAL_PATH}"
printf "Frozen capsule written to %s\n" "${FROZEN_PATH}"
printf "SHA256 digest written to %s\n" "${HASH_PATH}"
printf "Ledger events appended to %s\n" "${LEDGER_PATH}"
printf "HUD event appended to %s\n" "${HUD_PATH}"

unset LEDGER_TIMESTAMP LEDGER_DIGEST LEDGER_MAKER LEDGER_CHECKER TEMP_LEDGER_PATH
