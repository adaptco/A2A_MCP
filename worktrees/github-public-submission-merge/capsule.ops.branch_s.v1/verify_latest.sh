#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$DIR/.out"

if [[ ! -d "$OUT_DIR" ]]; then
  echo "No run artifacts found. Execute an action first." >&2
  exit 1
fi

latest_checksum="$(ls -t "$OUT_DIR"/*/checksums.sha256 2>/dev/null | head -n 1 || true)"
if [[ -z "$latest_checksum" ]]; then
  echo "No checksum archives found. Run apply/reissue first." >&2
  exit 1
fi

echo "🔍 Verifying manifests using $latest_checksum"
checksum_dir="$(dirname "$latest_checksum")"
( cd "$checksum_dir" && sha256sum -c checksums.sha256 )
