#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

LEDGER_BASE_URL="${LEDGER_BASE_URL:-http://localhost:3000}"
ARTIFACT_NAMES=("authority_map.v1" "capsule_remap.v1")

info() {
  printf '[pilot] %s\n' "$1"
}

error() {
  printf '[pilot][error] %s\n' "$1" >&2
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    error "Required command '$1' not found in PATH"
    exit 1
  fi
}

request_with_retry() {
  local method="$1"
  local url="$2"
  local data="${3:-}"
  local max_attempts=5
  local attempt=1
  local delay=1

  while [ $attempt -le $max_attempts ]; do
    local response
    if [ "$method" = "GET" ]; then
      response=$(curl -sS -w '\n%{http_code}' "$url" || true)
    else
      response=$(curl -sS -w '\n%{http_code}' -X "$method" -H 'Content-Type: application/json' --data "$data" "$url" || true)
    fi
    local status=$?
    if [ $status -eq 0 ]; then
      local http_code
      http_code=$(printf '%s' "$response" | tail -n1)
      local body
      body=$(printf '%s' "$response" | sed '$d')
      if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        printf '%s' "$body"
        return 0
      fi
      err_msg="HTTP $http_code from $url"
    else
      err_msg="curl error ($status) contacting $url"
    fi

    if [ $attempt -eq $max_attempts ]; then
      error "$err_msg"
      return 1
    fi

    info "Transient failure ($err_msg). Retrying in ${delay}s..."
    sleep "$delay"
    delay=$((delay * 2))
    attempt=$((attempt + 1))
  done
}

prepare_artifact() {
  local name="$1"
  local base="governance/${name}"
  local canonical="${base}.canonical.json"
  local hash_file="${base}.hash"
  local sig_file="${base}.sig"

  if [ ! -f "$canonical" ] || [ ! -f "$hash_file" ] || [ ! -f "$sig_file" ]; then
    error "Missing freeze outputs for ${name}. Run freeze scripts first."
    exit 1
  fi

  local hash
  hash=$(tr -d '\n' < "$hash_file")
  local signature
  signature=$(tr -d '\n' < "$sig_file")

  local payload
  payload=$(jq -n --arg name "$name" --arg hash "$hash" --arg signature "$signature" --rawfile canonical "$canonical" '{name:$name, hash:$hash, signature:$signature, canonical:$canonical}')

  printf '%s' "$payload"
}

for cmd in jq curl sha256sum; do
  require_cmd "$cmd"
done

if ! command -v cosign >/dev/null 2>&1 && [ -z "${SIGNER:-}" ]; then
  error "cosign is required for freeze scripts. Install cosign or set SIGNER to a signing command."
  exit 1
fi

info "Freezing authority map"
if ! scripts/freeze_authority_map.sh; then
  error "Failed to freeze authority map manifest"
  exit 1
fi

info "Freezing capsule remap"
if ! scripts/freeze_remap.sh; then
  error "Failed to freeze capsule remap manifest"
  exit 1
fi

for name in "${ARTIFACT_NAMES[@]}"; do
  info "Publishing freeze artifact for ${name}"
  payload=$(prepare_artifact "$name")
  response=$(request_with_retry POST "${LEDGER_BASE_URL}/ledger/freeze" "$payload") || {
    error "Unable to publish freeze artifact for ${name}"
    exit 1
  }
  stored_hash=$(printf '%s' "$response" | jq -r '.stored.hash')
  local_hash=$(printf '%s' "$payload" | jq -r '.hash')
  if [ "$stored_hash" != "$local_hash" ]; then
    error "Ledger stored hash ${stored_hash} does not match local hash ${local_hash} for ${name}"
    exit 1
  fi
  info "Ledger acknowledged ${name} with hash ${stored_hash}"
done

info "Requesting ledger snapshot"
snapshot=$(request_with_retry GET "${LEDGER_BASE_URL}/ledger/snapshot") || {
  error "Failed to fetch ledger snapshot"
  exit 1
}

proof_hash=$(printf '%s' "$snapshot" | jq -r '.proof.manifest_hash')
local_authority_hash=$(printf '%s' "$(prepare_artifact "authority_map.v1")" | jq -r '.hash')
if [ "$proof_hash" != "$local_authority_hash" ]; then
  error "Proof manifest hash ${proof_hash} does not match local authority map hash ${local_authority_hash}"
  exit 1
fi

missing_artifacts=0
for name in "${ARTIFACT_NAMES[@]}"; do
  expected_hash=$(printf '%s' "$(prepare_artifact "$name")" | jq -r '.hash')
  snapshot_hash=$(printf '%s' "$snapshot" | jq --arg name "$name" -r '.freeze_artifacts[] | select(.name==$name) | .hash' | head -n1)
  if [ -z "$snapshot_hash" ]; then
    error "Snapshot missing artifact entry for ${name}"
    missing_artifacts=1
    continue
  fi
  if [ "$snapshot_hash" != "$expected_hash" ]; then
    error "Snapshot hash ${snapshot_hash} for ${name} does not match expected ${expected_hash}"
    missing_artifacts=1
  fi
done

if [ "$missing_artifacts" -ne 0 ]; then
  error "Snapshot verification failed"
  exit 1
fi

info "Pilot workflow complete. Ledger snapshot is consistent with local freeze artifacts."
