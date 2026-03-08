#!/usr/bin/env bash
# Shared helpers for Branch-S capsule operations.
set -euo pipefail

BRANCH_S_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
OUT_ROOT="$BRANCH_S_DIR/.out"
LEDGER_PATH="$BRANCH_S_DIR/ledger.branch_s.jsonl"
CAPSULE_ID="capsule.prompt.designStudio.dual.v1"
CAPSULE_EPOCH="sentinel-100"

# Resolve repository root once so scripts can locate shared assets.
REPO_ROOT="$(git -C "$BRANCH_S_DIR" rev-parse --show-toplevel)"
DUAL_MANIFEST="$REPO_ROOT/capsules/capsule.prompt.designStudio.dual.v1.json"
QCAP_BUILDER="$REPO_ROOT/scripts/build_scrollstream_capsule_b.py"

# Attachments bundled into the Scrollstream Capsule Format B artifact.
BRANCH_S_ATTACHMENTS=(
  "$REPO_ROOT/capsules/capsule.metaagent.solf1.oneshot.v1.json:capsules/capsule.metaagent.solf1.oneshot.v1.json"
  "$REPO_ROOT/capsules/capsule.scene.designStudio.v1.json:capsules/capsule.scene.designStudio.v1.json"
  "$REPO_ROOT/capsules/runtime/templates/solf1_oneshot.tpl:templates/solf1_oneshot.tpl"
  "$REPO_ROOT/capsules/runtime/templates/design_studio_cinematic.tpl:templates/design_studio_cinematic.tpl"
)

mkdir -p "$OUT_ROOT"
touch "$LEDGER_PATH"

file_sha() {
  local path="$1"
  sha256sum "$path" | awk '{print $1}'
}

relpath_from_run() {
  local target="$1"
  python - "$RUN_DIR" "$target" <<'PY'
import os
base, target = os.sys.argv[1:3]
print(os.path.relpath(target, base))
PY
}

start_run() {
  local action="$1"
  TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  local safe_ts="${TIMESTAMP//[:]/}"  # remove colons for filesystem friendliness
  RUN_DIR="$OUT_ROOT/${safe_ts}_${action}"
  mkdir -p "$RUN_DIR"
  export TIMESTAMP
  export RUN_DIR
}

build_dual_capsule() {
  local output_path="$1"
  if [[ ! -f "$DUAL_MANIFEST" ]]; then
    echo "Primary dual prompt manifest missing: $DUAL_MANIFEST" >&2
    return 1
  fi
  local args=("$QCAP_BUILDER" --manifest "$DUAL_MANIFEST" --output "$output_path")
  for attachment in "${BRANCH_S_ATTACHMENTS[@]}"; do
    args+=(--attachment "$attachment")
  done
  python "${args[@]}"
}

write_checksums() {
  (cd "$RUN_DIR" && sha256sum "$@") > "$RUN_DIR/checksums.sha256"
}

write_single_checksum() {
  local file="$1"
  local destination="$2"
  sha256sum "$file" > "$destination"
}

append_ledger() {
  local action="$1"
  shift
  python - "$LEDGER_PATH" "$action" "$TIMESTAMP" "$RUN_DIR" "$CAPSULE_ID" "$@" <<'PY'
import json
import os
import sys
ledger, action, timestamp, run_dir, capsule_id = sys.argv[1:6]
extras = {}
for pair in sys.argv[6:]:
    key, value = pair.split('=', 1)
    if value == 'true':
        extras[key] = True
    elif value == 'false':
        extras[key] = False
    elif value == 'null':
        extras[key] = None
    else:
        extras[key] = value
entry = {
    "timestamp": timestamp,
    "action": action,
    "capsule": capsule_id,
    "run": os.path.relpath(run_dir, os.path.dirname(ledger)),
}
entry.update(extras)
with open(ledger, 'a', encoding='utf-8') as handle:
    json.dump(entry, handle)
    handle.write('\n')
PY
}

# Ensure TIMESTAMP and RUN_DIR are visible to sourced scripts.
export TIMESTAMP
export RUN_DIR
