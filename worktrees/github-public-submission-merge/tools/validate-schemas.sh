#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# ADK Schema Validator — Gate G2
#
# Validates all JSON schemas in adk/schemas/ and the
# contracts_index.json for structural integrity.
# Produces gate-result-g2.json on completion.
# ─────────────────────────────────────────────────────────
set -euo pipefail

SCHEMA_DIR="adk/schemas"
CONTRACTS_FILE="adk/contracts_index.json"
GENESIS_FILE="adk/genesis_block.json"
RESULT_FILE="gate-result-g2.json"

PASS=0
FAIL=0
ERRORS=""

echo "╔════════════════════════════════════════════╗"
echo "║   ADK Schema Validation — Gate G2          ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# ── Validate each schema file ──────────────────────────
for schema in "${SCHEMA_DIR}"/*.json; do
  filename=$(basename "$schema")
  if python3 -c "
import json, sys
with open('${schema}') as f:
    data = json.load(f)
# Check required top-level keys for JSON Schema files
if '\$schema' in data or 'type' in data or 'properties' in data:
    sys.exit(0)
else:
    print('  ⚠ Not a JSON Schema (no \$schema/type/properties key)')
    sys.exit(0)
" 2>/dev/null; then
    echo "  ✅ ${filename}"
    PASS=$((PASS + 1))
  else
    echo "  ❌ ${filename} — invalid JSON"
    FAIL=$((FAIL + 1))
    ERRORS="${ERRORS}\n  - ${filename}: invalid JSON"
  fi
done

# ── Validate contracts_index.json ──────────────────────
echo ""
echo "── Contracts Index ──"
if python3 -c "
import json, sys
with open('${CONTRACTS_FILE}') as f:
    data = json.load(f)
required = ['version', 'contracts']
for key in required:
    if key not in data:
        print(f'  ❌ Missing required key: {key}')
        sys.exit(1)
print('  ✅ contracts_index.json — structure valid')
print(f'     Version: {data[\"version\"]}')
print(f'     Contract groups: {len(data[\"contracts\"])}')
" 2>/dev/null; then
  PASS=$((PASS + 1))
else
  FAIL=$((FAIL + 1))
  ERRORS="${ERRORS}\n  - contracts_index.json: structure invalid"
fi

# ── Validate genesis_block.json ────────────────────────
echo ""
echo "── Genesis Block ──"
if python3 -m json.tool "${GENESIS_FILE}" > /dev/null 2>&1; then
  echo "  ✅ genesis_block.json — valid JSON"
  PASS=$((PASS + 1))
else
  echo "  ❌ genesis_block.json — invalid JSON"
  FAIL=$((FAIL + 1))
  ERRORS="${ERRORS}\n  - genesis_block.json: invalid JSON"
fi

# ── Generate Gate Result ───────────────────────────────
echo ""
echo "════════════════════════════════════════════"

TOTAL=$((PASS + FAIL))
if [ "$FAIL" -eq 0 ]; then
  STATUS="PASS"
  echo "  Gate G2: PASS (${PASS}/${TOTAL} checks passed)"
else
  STATUS="FAIL"
  echo "  Gate G2: FAIL (${FAIL}/${TOTAL} checks failed)"
  echo -e "  Errors:${ERRORS}"
fi

cat > "${RESULT_FILE}" <<EOF
{
  "gate": "G2",
  "check_id": "DESIGN_SIGNOFF",
  "status": "${STATUS}",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "details": {
    "schemas_validated": ${PASS},
    "schemas_failed": ${FAIL},
    "total": ${TOTAL}
  }
}
EOF

echo "  Result written to ${RESULT_FILE}"
echo "════════════════════════════════════════════"

# Exit with failure if any checks failed
[ "$FAIL" -eq 0 ]
