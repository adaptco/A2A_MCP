#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CAPSULE_PATH="${ROOT_DIR}/capsules/doctrine/capsule.wrapper.adaptco_os.v1.json"
CANON_SCRIPT="${ROOT_DIR}/scripts/canonicalize_manifest.py"
OUTPUT_DIR="${ROOT_DIR}/runtime"
CANONICAL_PATH="${OUTPUT_DIR}/capsule.wrapper.adaptco_os.v1.canonical.json"
HASH_PATH="${OUTPUT_DIR}/capsule.wrapper.adaptco_os.v1.sha256"
LEDGER_PATH="${OUTPUT_DIR}/scrollstream_ledger.jsonl"

if [[ ! -f "${CAPSULE_PATH}" ]]; then
  echo "Wrapper capsule not found at ${CAPSULE_PATH}" >&2
  exit 1
fi

if [[ ! -f "${CANON_SCRIPT}" ]]; then
  echo "Canonicalization script not found at ${CANON_SCRIPT}" >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"

python3 "${CANON_SCRIPT}" < "${CAPSULE_PATH}" > "${CANONICAL_PATH}"
HASH=$(sha256sum "${CANONICAL_PATH}" | cut -d' ' -f1)
printf "%s" "${HASH}" > "${HASH_PATH}"

timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
export LEDGER_TIMESTAMP="${timestamp}"
export CANONICAL_PATH
export HASH_PATH
python3 - <<'PY' >> "${LEDGER_PATH}"
import json
import os
import sys

timestamp = os.environ["LEDGER_TIMESTAMP"]
canon_path = os.environ["CANONICAL_PATH"]
hash_path = os.environ["HASH_PATH"]
with open(hash_path, "r", encoding="utf-8") as handle:
    digest = handle.read().strip()
entry = {
    "timestamp": timestamp,
    "event": "wrapper.freeze",
    "capsule": "capsule.wrapper.adaptco_os.v1",
    "canonical": os.path.relpath(canon_path, os.path.dirname(canon_path)),
    "hash": digest,
}
json.dump(entry, sys.stdout, ensure_ascii=False)
sys.stdout.write("\n")
PY

printf "Canonical wrapper written to %s\n" "${CANONICAL_PATH}"
printf "SHA256 hash written to %s\n" "${HASH_PATH}"
printf "Ledger entry appended to %s\n" "${LEDGER_PATH}"

unset LEDGER_TIMESTAMP CANONICAL_PATH HASH_PATH
