#!/usr/bin/env bash
set -euo pipefail

CANONICAL_FILE="avatar_bindings.v1.canonical.json"
HASH_FILE="avatar_bindings.v1.hash"
SIGNATURE_FILE="avatar_bindings.v1.maker.sig"

if [[ -z "${MAKER_KEY:-}" ]]; then
  echo "MAKER_KEY environment variable is not set" >&2
  exit 1
fi

if [[ ! -f "${CANONICAL_FILE}" ]]; then
  echo "Canonical manifest ${CANONICAL_FILE} not found" >&2
  exit 1
fi

if ! python3 - <<'PYEOF'
import nacl  # noqa: F401
PYEOF
then
  echo "PyNaCl is required (install with: pip install pynacl)" >&2
  exit 1
fi

HASH=$(sha256sum "${CANONICAL_FILE}" | cut -d' ' -f1)
python3 - "$CANONICAL_FILE" "$MAKER_KEY" >"${SIGNATURE_FILE}" <<'PYEOF'
import base64
import sys
from pathlib import Path

from nacl.signing import SigningKey

canon_path = Path(sys.argv[1])
seed_b64 = sys.argv[2]

seed = base64.b64decode(seed_b64)
key = SigningKey(seed)
signature = key.sign(canon_path.read_bytes()).signature
print(base64.b64encode(signature).decode("utf-8"))
PYEOF

echo "${HASH}" >"${HASH_FILE}"
