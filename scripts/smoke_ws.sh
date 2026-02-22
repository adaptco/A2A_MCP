#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
RUN_PASS="smoke-pass"
RUN_FAIL="smoke-fail"

echo "[smoke] health check"
curl -fsS "$BASE_URL/health" >/dev/null

echo "[smoke] PASS scenario (requires ws harness server implementation)"
echo '{"type":"render_request","run_id":"'"$RUN_PASS"'","payload":{"assets":["staging/mock/pass.png"]}}' \
  | python scripts/ws_client.py --url "${WS_URL:-ws://localhost:8000/ws/pipeline}" --expect pipeline.pass

echo "[smoke] FAIL scenario (assert no export.completed)"
echo '{"type":"render_request","run_id":"'"$RUN_FAIL"'","payload":{"assets":["staging/mock/fail.png"],"force_fail_gate":"c5"}}' \
  | python scripts/ws_client.py --url "${WS_URL:-ws://localhost:8000/ws/pipeline}" --expect pipeline.halted --reject export.completed

echo "[smoke] verify no export for fail run"
if compgen -G "exports/${RUN_FAIL}*" > /dev/null; then
  echo "FAIL: export artifacts detected for halted run"
  exit 1
fi

echo "[smoke] complete"
