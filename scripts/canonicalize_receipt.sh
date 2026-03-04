#!/usr/bin/env bash
set -euo pipefail

in="$1"
out="$2"

# Canonicalize (stable key ordering + stable formatting)
jq -S . "$in" > "$out"
