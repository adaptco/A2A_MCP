#!/usr/bin/env bash
set -euo pipefail

log_path="${SEAL_ROOT_LOG:?SEAL_ROOT_LOG not set}"
{
  printf 'invocation %s\n' "$(date -Iseconds)"
  printf 'args: %s\n' "$*"
  printf 'MERKLE_ROOT=%s\n' "${MERKLE_ROOT:-}"
  if [ -n "${MERKLE_PAYLOAD:-}" ]; then
    printf '%s\n' "$MERKLE_PAYLOAD"
  fi
} >>"$log_path"
