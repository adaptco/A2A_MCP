#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
MANIFEST="${ROOT_DIR}/avatar_bindings.v1.json"
CANON_SCRIPT="${ROOT_DIR}/scripts/canonicalize_manifest.py"
OUTPUT_DIR="${ROOT_DIR}/governance"
CANONICAL="${OUTPUT_DIR}/avatar_bindings.v1.canonical.json"
HASH_FILE="${OUTPUT_DIR}/avatar_bindings.v1.hash"
SIG_FILE="${OUTPUT_DIR}/avatar_bindings.v1.sig"
SIGNING_KEY="${OUTPUT_DIR}/test-ed25519.pem"
PUBLIC_DIR="${ROOT_DIR}/public/data"
PUBLIC_MANIFEST="${PUBLIC_DIR}/avatar_bindings.v1.json"

if [[ ! -f "${MANIFEST}" ]]; then
  echo "Avatar bindings manifest not found at ${MANIFEST}" >&2
  exit 1
fi

if [[ ! -f "${CANON_SCRIPT}" ]]; then
  echo "Canonicalization script not found at ${CANON_SCRIPT}" >&2
  exit 1
fi

if [[ ! -f "${SIGNING_KEY}" ]]; then
  echo "Signing key not found at ${SIGNING_KEY}" >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"
mkdir -p "${PUBLIC_DIR}"

python3 "${CANON_SCRIPT}" < "${MANIFEST}" > "${CANONICAL}"
HASH=$(sha256sum "${CANONICAL}" | cut -d' ' -f1)
printf "%s" "${HASH}" > "${HASH_FILE}"

cp "${MANIFEST}" "${PUBLIC_MANIFEST}"

TMP_SIG=$(mktemp)
trap 'rm -f "${TMP_SIG}"' EXIT
openssl pkeyutl -sign -inkey "${SIGNING_KEY}" -in "${CANONICAL}" -out "${TMP_SIG}" -rawin
base64 -w0 "${TMP_SIG}" > "${SIG_FILE}"
echo >> "${SIG_FILE}"

printf "Canonical manifest written to %s\\n" "${CANONICAL}"
printf "SHA256 hash written to %s\\n" "${HASH_FILE}"
printf "Signature written to %s\\n" "${SIG_FILE}"
