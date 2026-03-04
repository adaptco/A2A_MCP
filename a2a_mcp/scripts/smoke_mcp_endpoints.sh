#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
AUTH_TOKEN="${AUTH_TOKEN:-}"

if [[ -z "$AUTH_TOKEN" ]]; then
  echo "AUTH_TOKEN must be set"
  exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

unauth_check() {
  local endpoint="$1"
  local body_file="$2"
  local code

  code=$(curl -sS -o "$TMP_DIR/unauth.out" -w '%{http_code}' \
    -X POST "$BASE_URL$endpoint" \
    -H 'Content-Type: application/json' \
    --data-binary "@$body_file")

  if [[ "$code" == "401" || "$code" == "403" ]]; then
    echo "[ok] unauth rejected for $endpoint (status=$code)"
  else
    echo "[fail] expected 401/403 for $endpoint, got $code"
    cat "$TMP_DIR/unauth.out"
    exit 1
  fi
}

auth_check() {
  local endpoint="$1"
  local body_file="$2"
  local label="$3"
  local code

  code=$(curl -sS -o "$TMP_DIR/$label.out" -w '%{http_code}' \
    -X POST "$BASE_URL$endpoint" \
    -H 'Content-Type: application/json' \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    --data-binary "@$body_file")

  if [[ "$code" =~ ^2[0-9][0-9]$ ]]; then
    python - <<PY
import json
from pathlib import Path
p = Path("$TMP_DIR/$label.out")
raw = p.read_text().strip()
if not raw:
    raise SystemExit("empty response body")
try:
    json.loads(raw)
except json.JSONDecodeError as exc:
    raise SystemExit(f"non-JSON response: {exc}")
print("[ok] $label succeeded with JSON response (status=$code)")
PY
  else
    echo "[fail] $label expected 2xx, got $code"
    cat "$TMP_DIR/$label.out"
    exit 1
  fi
}

cat > "$TMP_DIR/mcp.json" <<'JSON'
{
  "jsonrpc": "2.0",
  "id": "smoke-mcp",
  "method": "ping",
  "params": {}
}
JSON

cat > "$TMP_DIR/tools_call.json" <<'JSON'
{
  "jsonrpc": "2.0",
  "id": "smoke-tools",
  "method": "tools/call",
  "params": {
    "name": "trigger_new_research",
    "arguments": {
      "goal": "smoke test"
    }
  }
}
JSON

cat > "$TMP_DIR/tools_call_large.json" <<'JSON'
{
  "jsonrpc": "2.0",
  "id": "smoke-tools-shaped",
  "method": "tools/call",
  "params": {
    "name": "trigger_new_research",
    "arguments": {
      "goal": "token shaping smoke test with intentionally long prompt payload to validate bounded shaping behavior and response integrity"
    }
  }
}
JSON

echo "[smoke] unauth authz checks"
unauth_check "/mcp" "$TMP_DIR/mcp.json"
unauth_check "/tools/call" "$TMP_DIR/tools_call.json"

echo "[smoke] authorized success checks"
auth_check "/mcp" "$TMP_DIR/mcp.json" "mcp"
auth_check "/tools/call" "$TMP_DIR/tools_call.json" "tools_call"
auth_check "/tools/call" "$TMP_DIR/tools_call_large.json" "tools_call_shaping"

echo "[smoke] complete"
