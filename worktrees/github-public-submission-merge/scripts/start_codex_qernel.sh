#!/usr/bin/env bash
# Launch the CODEX qernel HTTP server for AxQxOS.
set -euo pipefail
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$BASE_DIR${PYTHONPATH:+:$PYTHONPATH}"
cd "$BASE_DIR"
exec python app/server.py "$@"
