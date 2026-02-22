#!/usr/bin/env bash

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "[seal_root] usage: $0 <merkle_root>" >&2
  exit 1
fi

MERKLE_ROOT="$1"
PAYLOAD="${MERKLE_PAYLOAD:-}"
LOG_DEST="${SEAL_ROOT_LOG:-}"

printf '[seal_root] Sealing Merkle root %s\n' "$MERKLE_ROOT"

if [ -n "$LOG_DEST" ]; then
  {
    printf 'MERKLE_ROOT=%s\n' "$MERKLE_ROOT"
    if [ -n "$PAYLOAD" ]; then
      printf '%s\n' "$PAYLOAD"
    fi
  } >>"$LOG_DEST"
fi
