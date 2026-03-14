#!/usr/bin/env bash
# patch_resolver.sh — set cockpit-first resolution and vault-aware lineage
set -euo pipefail

RESOLVER="${1:-resolver.runtime.v1.json}"
COCKPIT_CAPSULE_ID="${2:-capsule.map.qube.endtoend.v1}"
REGISTRY_PATH="${3:-capsules/runtime/capsule.registry.runtime.v1.json}"
VAULT_PATH="${4:-relay.artifacts.v1.json}"
LEDGER_AUDIT="${5:-.out/resolver.audit.jsonl}"

ts(){ date -u +"%Y-%m-%dT%H:%M:%SZ"; }

resolve_id(){
  local file="$1"
  if [ -f "$file" ]; then
    jq -r '(.capsule_id // .artifact_id // .resolver_id // empty)' "$file" 2>/dev/null || true
  fi
}

REGISTRY_ID=$(resolve_id "$REGISTRY_PATH")
if [ -z "$REGISTRY_ID" ]; then
  REGISTRY_ID="$(basename "$REGISTRY_PATH" .json)"
fi

VAULT_ID=$(resolve_id "$VAULT_PATH")
if [ -z "$VAULT_ID" ]; then
  VAULT_ID="$(basename "$VAULT_PATH" .json)"
fi

if [ ! -f "$RESOLVER" ]; then
  cat > "$RESOLVER" <<'JSON'
{
  "resolver_id": "resolver.runtime.v1",
  "version": "1.0.0",
  "priority_stack": [],
  "policies": {}
}
JSON
fi

tmp=$(mktemp)
jq --arg cockpit "$COCKPIT_CAPSULE_ID" --arg reg "$REGISTRY_ID" --arg vault "$VAULT_ID" '
  .priority_stack = [$cockpit, "ssot.registry.v7", $vault, $reg, "capsule.motion.ledger.v1"] |
  .policies = {
    graph_aware: { env_bound: true, fail_closed_on_mismatch: true },
    motion_binding: { require_sealed: true, enforce_fps: true, attach_qlock_ticks: true },
    duplicate_guard: { idempotency_key: ["event", "capsule", "digest"], prefer: "earliest" }
  }
' "$RESOLVER" > "$tmp"
mv "$tmp" "$RESOLVER"

echo "{\"ts\":\"$(ts)\",\"event\":\"resolver.patch.v1\",\"resolver_id\":\"resolver.runtime.v1\",\"cockpit\":\"$COCKPIT_CAPSULE_ID\"}" >> "$LEDGER_AUDIT"

echo "✅ Resolver patched → cockpit-first"
