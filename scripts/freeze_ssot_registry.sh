#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CAPSULE_PATH="${ROOT_DIR}/capsules/registry/capsule.ssot.registry.v1.json"
CANON_SCRIPT="${ROOT_DIR}/scripts/canonicalize_manifest.py"
OUTPUT_DIR="${ROOT_DIR}/runtime"
CANONICAL_PATH="${OUTPUT_DIR}/capsule.ssot.registry.v1.canonical.json"
HASH_PATH="${OUTPUT_DIR}/capsule.ssot.registry.v1.sha256"
LEDGER_PATH="${OUTPUT_DIR}/scrollstream_ledger.jsonl"
RUNTIME_REGISTRY_PATH="${OUTPUT_DIR}/capsule.registry.runtime.v1.json"

if [[ ! -f "${CAPSULE_PATH}" ]]; then
  echo "SSOT registry capsule not found at ${CAPSULE_PATH}" >&2
  exit 1
fi

if [[ ! -f "${CANON_SCRIPT}" ]]; then
  echo "Canonicalization script not found at ${CANON_SCRIPT}" >&2
  exit 1
fi

if [[ ! -f "${RUNTIME_REGISTRY_PATH}" ]]; then
  echo "Runtime registry not found at ${RUNTIME_REGISTRY_PATH}" >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"

python3 "${CANON_SCRIPT}" < "${CAPSULE_PATH}" > "${CANONICAL_PATH}"
HASH=$(sha256sum "${CANONICAL_PATH}" | cut -d' ' -f1)
printf "%s" "${HASH}" > "${HASH_PATH}"

CANON_RELATIVE=$(python3 -c "import os; print(os.path.relpath('${CANONICAL_PATH}', '${ROOT_DIR}'))")

CANON_RUNTIME_RELATIVE=$(python3 -c "import os; print(os.path.relpath('${CANONICAL_PATH}', '${OUTPUT_DIR}'))")

timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
export LEDGER_TIMESTAMP="${timestamp}"
export HASH_VALUE="${HASH}"
export CANON_RUNTIME_RELATIVE
export ROOT_DIR
python3 - <<'PY' >> "${LEDGER_PATH}"
import json
import os
import sys

timestamp = os.environ["LEDGER_TIMESTAMP"]
canon_rel = os.environ["CANON_RUNTIME_RELATIVE"]
hash_value = os.environ["HASH_VALUE"]
entries = [
    {
        "timestamp": timestamp,
        "event": "capsule.seal.v1",
        "capsule": "ssot.registry.v1",
        "digest": f"sha256:{hash_value}"
    },
    {
        "timestamp": timestamp,
        "event": "ssot.registry.freeze.v1",
        "capsule": "ssot.registry.v1",
        "canonical": canon_rel,
        "hash": hash_value
    }
]
for entry in entries:
    json.dump(entry, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
PY

export CANON_RELATIVE HASH_VALUE LEDGER_TIMESTAMP ROOT_DIR
python3 - <<'PY'
import json
import os
from pathlib import Path

root = Path(os.environ["ROOT_DIR"])
registry_path = root / "runtime" / "capsule.registry.runtime.v1.json"
canon_rel = os.environ["CANON_RELATIVE"]
hash_value = os.environ["HASH_VALUE"]
timestamp = os.environ["LEDGER_TIMESTAMP"]

with registry_path.open("r", encoding="utf-8") as handle:
    data = json.load(handle)

entries = data.setdefault("entries", [])
for entry in entries:
    if entry.get("capsule_id") == "ssot.registry.v1":
        entry["canonical"] = canon_rel
        entry["hash"] = hash_value
        entry["status"] = "SEALED"
        entry["updated_at"] = timestamp
        governance = entry.get("governance") or {}
        if "steward" not in governance:
            governance["steward"] = "Q.Enterprise Council"
        entry["governance"] = governance
        break
else:
    entries.append({
        "capsule_id": "ssot.registry.v1",
        "canonical": canon_rel,
        "hash": hash_value,
        "status": "SEALED",
        "updated_at": timestamp,
        "governance": {"steward": "Q.Enterprise Council"}
    })

with registry_path.open("w", encoding="utf-8") as handle:
    json.dump(data, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
PY

unset LEDGER_TIMESTAMP HASH_VALUE CANON_RELATIVE CANON_RUNTIME_RELATIVE

printf "Canonical SSOT registry written to %s\n" "${CANONICAL_PATH}"
printf "SHA256 hash written to %s\n" "${HASH_PATH}"
printf "Runtime registry updated at %s\n" "${RUNTIME_REGISTRY_PATH}"
printf "Ledger entry appended to %s\n" "${LEDGER_PATH}"
