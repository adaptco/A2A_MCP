#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/staging"

sha256_file() {
  python - <<'PY'
import hashlib, sys
p=sys.argv[1]
try:
    with open(p,'rb') as f:
        h=hashlib.sha256(f.read()).hexdigest()
    print(h)
except Exception as e:
    sys.exit(1)
PY
}

for fx_dir in "${ROOT}/tests/receipts/cases/"*; do
  case_id="$(basename "$fx_dir")"
  echo "== Receipts: ${case_id}"

  run_dir="${OUT}/${case_id}"
  if [ ! -f "${run_dir}/receipt.json" ]; then
    echo "Error: ${run_dir}/receipt.json not found"
    exit 1
  fi

  "${ROOT}/scripts/canonicalize_receipt.sh" \
    "${run_dir}/receipt.json" \
    "${run_dir}/receipt.canonical.json"

  actual_sha="$(sha256_file "${run_dir}/receipt.canonical.json")"
  echo "${actual_sha}" > "${run_dir}/receipt.sha256"

  # Compare canonical receipt bytes
  diff -u "${fx_dir}/expected.canonical.json" "${run_dir}/receipt.canonical.json"

  # Compare sha
  diff -u "${fx_dir}/expected.sha256" "${run_dir}/receipt.sha256"

  # Optional: validate transition block surface only
  if [ -f "${fx_dir}/expected.transition.json" ]; then
    jq -S '.transition_block' "${run_dir}/receipt.canonical.json" > "${run_dir}/transition_block.json"
    diff -u "${fx_dir}/expected.transition.json" "${run_dir}/transition_block.json"
  fi
done

echo "✅ Receipt validator passed"
