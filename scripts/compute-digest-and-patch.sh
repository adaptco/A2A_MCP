#!/usr/bin/env bash
# compute-digest-and-patch.sh
# Usage: ./compute-digest-and-patch.sh draft.jsonl > checkpoint.v2.preview.final.jsonl

set -euo pipefail
INPUT="${1:-draft.jsonl}"

# Compute digest from canonical JSON (no content_hash)
DIGEST=$(jq -cS 'del(.content_hash)' "$INPUT" | sha256sum | awk '{print $1}')
CONTENT_HASH="sha256:${DIGEST}"

# Insert digest back into JSON
jq --arg ch "$CONTENT_HASH" '. + {content_hash: $ch}' "$INPUT"
