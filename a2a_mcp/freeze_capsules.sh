#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <capsule-json>" >&2
  exit 1
fi

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TARGET_ARG="$1"

CANON_SCRIPT="${ROOT_DIR}/scripts/canonicalize_manifest.py"
MANIFEST_PATH="${ROOT_DIR}/runtime/freeze_manifest.json"
FROZEN_DIR="${ROOT_DIR}/runtime/frozen"

if [[ ! -f "${CANON_SCRIPT}" ]]; then
  echo "Canonicalization script missing at ${CANON_SCRIPT}" >&2
  exit 1
fi

if [[ ! -f "${MANIFEST_PATH}" ]]; then
  echo "{}" > "${MANIFEST_PATH}"
fi

if [[ -f "${TARGET_ARG}" ]]; then
  SOURCE_PATH="${TARGET_ARG}"
else
  SOURCE_PATH=$(cd "${ROOT_DIR}" && find capsules -type f -name "${TARGET_ARG}" | head -n1 || true)
  if [[ -z "${SOURCE_PATH}" ]]; then
    echo "Capsule definition ${TARGET_ARG} not found" >&2
    exit 1
  fi
  SOURCE_PATH="${ROOT_DIR}/${SOURCE_PATH}"
fi

if [[ ! -f "${SOURCE_PATH}" ]]; then
  echo "Capsule definition not found at ${SOURCE_PATH}" >&2
  exit 1
fi

mkdir -p "${FROZEN_DIR}"
BASENAME=$(basename "${SOURCE_PATH}")
FROZEN_PATH="${FROZEN_DIR}/${BASENAME}"

python3 "${CANON_SCRIPT}" < "${SOURCE_PATH}" > "${FROZEN_PATH}"
HASH=$(sha256sum "${FROZEN_PATH}" | cut -d' ' -f1)

python3 - "$MANIFEST_PATH" "runtime/frozen/${BASENAME}" "${HASH}" <<'PY'
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
key = sys.argv[2]
hash_value = sys.argv[3]

if manifest_path.exists():
    with manifest_path.open() as fh:
        data = json.load(fh)
else:
    data = {}

data[key] = hash_value

with manifest_path.open("w") as fh:
    json.dump({k: data[k] for k in sorted(data)}, fh, indent=2)
    fh.write("\n")
PY

printf "Frozen capsule written to %s\n" "${FROZEN_PATH}"
printf "SHA256 hash recorded in %s under key %s\n" "${MANIFEST_PATH}" "runtime/frozen/${BASENAME}"
