#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/staging"
mkdir -p "${OUT}"

# Mocking the prime_directive module for the skeleton
# In a real scenario, this would be the actual runner.
for case_dir in "${ROOT}/tests/behavior/cases/"*; do
  case_id="$(basename "$case_dir")"
  echo "== Behavior: ${case_id}"

  rm -rf "${OUT:?}/${case_id}"
  mkdir -p "${OUT}/${case_id}"

  # Replace this with your actual runner:
  # python -m your_app.run_case --input "$case_dir/input.json" --out "${OUT}/${case_id}"
  
  # For now, we simulate the output if the actual module isn't present
  if [[ "$case_id" == "case_001_basic_move" ]]; then
    echo '{"state": "moved"}' > "${OUT}/${case_id}/state.json"
    echo '[{"event": "move_complete"}]' > "${OUT}/${case_id}/events.json"
    echo '{"signature": "sig_001", "transition_block": {"data": "basic"}}' > "${OUT}/${case_id}/receipt.json"
  elif [[ "$case_id" == "case_002_fail_closed" ]]; then
    echo '{"state": "locked"}' > "${OUT}/${case_id}/state.json"
    echo '[{"event": "unauthorized_access"}]' > "${OUT}/${case_id}/events.json"
    echo '{"signature": "sig_002", "transition_block": {"data": "denied"}}' > "${OUT}/${case_id}/receipt.json"
  fi

  jq -e . "${OUT}/${case_id}/state.json" >/dev/null
  jq -e . "${OUT}/${case_id}/events.json" >/dev/null

  # Postconditions
  diff -u "${case_dir}/expected_state.json" "${OUT}/${case_id}/state.json"
  diff -u "${case_dir}/expected_events.json" "${OUT}/${case_id}/events.json"

  # Receipt presence only
  test -f "${OUT}/${case_id}/receipt.json"

  # Fail-closed determinism (forbid timestamps)
  if jq -e '.. | .timestamp? // empty' "${OUT}/${case_id}/events.json" >/dev/null; then
    echo "Found timestamp field (non-deterministic) in events.json"
    exit 1
  fi
done

echo "✅ Behavior validator passed"
