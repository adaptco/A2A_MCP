#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CAPSULE_PATH="${ROOT_DIR}/capsules/prompt/capsule.prompt.graph.lego_f1.sf23_vs_w14.v1.json"
CANON_SCRIPT="${ROOT_DIR}/scripts/canonicalize_manifest.py"
OUTPUT_DIR="${ROOT_DIR}/runtime"
CANONICAL_PATH="${OUTPUT_DIR}/capsule.prompt.graph.lego_f1.sf23_vs_w14.v1.canonical.json"
HASH_PATH="${OUTPUT_DIR}/capsule.prompt.graph.lego_f1.sf23_vs_w14.v1.sha256"
LEDGER_PATH="${OUTPUT_DIR}/scrollstream_ledger.jsonl"

if [[ ! -f "${CAPSULE_PATH}" ]]; then
  echo "Prompt graph capsule not found at ${CAPSULE_PATH}" >&2
  exit 1
fi

if [[ ! -f "${CANON_SCRIPT}" ]]; then
  echo "Canonicalization script not found at ${CANON_SCRIPT}" >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"

python3 "${CANON_SCRIPT}" < "${CAPSULE_PATH}" > "${CANONICAL_PATH}"
HASH=$(sha256sum "${CANONICAL_PATH}" | cut -d' ' -f1)
printf "%s\n" "${HASH}" > "${HASH_PATH}"

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
export LEDGER_TIMESTAMP="${TIMESTAMP}"
export HASH_VALUE="${HASH}"
python3 - <<'PY' >> "${LEDGER_PATH}"
import json
import os
import sys

timestamp = os.environ["LEDGER_TIMESTAMP"]
digest = os.environ["HASH_VALUE"]
entries = [
    {
        "timestamp": timestamp,
        "event": "capsule.seal.v1",
        "capsule": "capsule.prompt.graph.lego_f1.sf23_vs_w14.v1",
        "hash": digest,
    },
    {
        "timestamp": timestamp,
        "event": "prompt.graph.freeze.v1",
        "capsule": "capsule.prompt.graph.lego_f1.sf23_vs_w14.v1",
        "runtime": "lego_f1.highlight",
        "hash": digest,
        "status": "staged",
    },
]
for entry in entries:
    json.dump(entry, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
PY

printf "Canonical prompt graph written to %s\n" "${CANONICAL_PATH}"
printf "SHA256 hash written to %s\n" "${HASH_PATH}"
printf "Ledger entries appended to %s\n" "${LEDGER_PATH}"

unset LEDGER_TIMESTAMP HASH_VALUE
