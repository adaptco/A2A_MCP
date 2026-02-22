#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
. "$SCRIPT_DIR/_freeze_common.sh"

remap_manifest="$ROOT_DIR/governance/capsule_remap.v1.json"
if [ ! -f "$remap_manifest" ]; then
  printf '%s\n' "Manifest not found: $remap_manifest" >&2
  exit 1
fi

freeze_manifest "$remap_manifest" "capsule_remap.v1"
