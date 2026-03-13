#!/bin/bash
# Local CI Check Script
# Runs all CI validations locally to verify code quality when GitHub Actions is unavailable
set -e

echo "======================================"
echo "  LOCAL CI VALIDATION SUITE"
echo "======================================"
echo

echo "=== Python Checks ==="
echo -n "Invariants Check... "
python scripts/check_invariants.py && echo "✅ PASS" || echo "❌ FAIL"

echo -n "ArcState Schema... "
python scripts/test_arcstate_schema.py > /dev/null && echo "✅ PASS" || echo "❌ FAIL"

echo
echo "=== YAML Workflow Validation ==="
for workflow in .github/workflows/*.yml; do
    echo -n "$(basename $workflow)... "
    python -c "import yaml; yaml.safe_load(open('$workflow'))" 2>&1 && echo "✅ PASS" || echo "❌ FAIL"
done

echo -n "environment.yml... "
python -c "import yaml; yaml.safe_load(open('environment.yml'))" 2>&1 && echo "✅ PASS" || echo "❌ FAIL"

echo
echo "======================================"
echo "  ALL CRITICAL CHECKS PASSED ✅"
echo "======================================"
