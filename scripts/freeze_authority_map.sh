#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/_freeze_common.sh"

authority_manifest="$ROOT_DIR/governance/authority_map.v1.json"
if [ ! -f "$authority_manifest" ]; then
  printf '%s\n' "Manifest not found: $authority_manifest" >&2
  exit 1
fi

freeze_manifest "$authority_manifest" "authority_map.v1"
