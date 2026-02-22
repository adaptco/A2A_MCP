#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 --profile <profile_id> --input <payloads.jsonl|payloads.ndjson|input_dir>" >&2
  exit 1
}

PROFILE=""
INPUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="${2:-}"
      shift 2
      ;;
    --input)
      INPUT="${2:-}"
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

if [[ -z "$PROFILE" || -z "$INPUT" ]]; then
  usage
fi

export PROFILE
export INPUT

profile_data=$(python - <<'PY'
import json
import os
import shlex
from pathlib import Path

profile_id = os.environ["PROFILE"]
manifest = Path("manifests/content_integrity_eval.json")
profiles = json.loads(manifest.read_text()).get("cliProfiles", [])
profile = next((item for item in profiles if item.get("id") == profile_id), None)
if profile is None:
    raise SystemExit(f"Unknown profile: {profile_id}")

command = profile.get("command", "")
parts = shlex.split(command)

manifest_path = "manifests/content_integrity_eval.json"
output_path = None

for idx, part in enumerate(parts):
    if part == "--manifest" and idx + 1 < len(parts):
        manifest_path = parts[idx + 1]
    if part == "--output" and idx + 1 < len(parts):
        output_path = parts[idx + 1]

if output_path is None:
    raise SystemExit("Profile command missing --output")

print(f"{manifest_path}|{output_path}")
PY
)

MANIFEST_PATH="${profile_data%%|*}"
OUTPUT_PATH="${profile_data##*|}"

export MANIFEST_PATH

python - <<'PY'
import json
import os
from pathlib import Path

input_path = Path(os.environ["INPUT"])
manifest_path = Path(os.environ["MANIFEST_PATH"])
routing_path = Path("registry/routing/routing_policy.v1.json")

manifest = json.loads(manifest_path.read_text())
contract = manifest.get("audit_inputs", {}).get("input_contract", {})
required_blocks = set(contract.get("required_blocks", []))
metadata_fields = set(contract.get("metadata_fields", []))

routing = json.loads(routing_path.read_text())
chains = routing.get("module_chains", {})
cie_chain = chains.get("content.integrity.eval.v1")
if not cie_chain:
    raise SystemExit("Routing policy missing content.integrity.eval.v1 chain")
if cie_chain.get("routing_order") != ["synthetic.noise.injector.v1", "synthetic.contradiction.synth.v1"]:
    raise SystemExit("Routing policy order mismatch for content.integrity.eval.v1")
if cie_chain.get("fallbacks"):
    raise SystemExit("Routing policy contains fallbacks for content.integrity.eval.v1")

if not input_path.exists():
    raise SystemExit(f"Missing input payloads: {input_path}")

if input_path.is_dir():
    ndjson_path = input_path / "payloads.ndjson"
    jsonl_path = input_path / "payloads.jsonl"
    metadata_path = input_path / "metadata.json"
    if not metadata_path.exists():
        raise SystemExit(f"Missing metadata.json in {input_path}")
    if ndjson_path.exists():
        payloads_path = ndjson_path
    elif jsonl_path.exists():
        payloads_path = jsonl_path
    else:
        raise SystemExit(f"Missing payloads.ndjson or payloads.jsonl in {input_path}")
else:
    payloads_path = input_path

for idx, line in enumerate(payloads_path.read_text().splitlines(), start=1):
    if not line.strip():
        continue
    payload = json.loads(line)
    missing = required_blocks.difference(payload)
    if missing:
        raise SystemExit(f"Payload line {idx} missing blocks: {sorted(missing)}")
    metadata = payload.get("metadata", {})
    missing_meta = metadata_fields.difference(metadata)
    if missing_meta:
        raise SystemExit(f"Payload line {idx} missing metadata fields: {sorted(missing_meta)}")
print("Pre-run invariants satisfied.")
PY

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

export TMP_DIR

python - <<'PY'
import json
import os
from pathlib import Path

input_path = Path(os.environ["INPUT"])
output_dir = Path(os.environ["TMP_DIR"])

if input_path.is_dir():
    ndjson_path = input_path / "payloads.ndjson"
    jsonl_path = input_path / "payloads.jsonl"
    metadata_path = input_path / "metadata.json"
    if not metadata_path.exists():
        raise SystemExit(f"Missing metadata.json in {input_path}")
    if ndjson_path.exists():
        payloads_path = ndjson_path
    elif jsonl_path.exists():
        payloads_path = jsonl_path
    else:
        raise SystemExit(f"Missing payloads.ndjson or payloads.jsonl in {input_path}")
else:
    payloads_path = input_path

for idx, line in enumerate(payloads_path.read_text().splitlines(), start=1):
    if not line.strip():
        continue
    payload = json.loads(line)
    out_path = output_dir / f"payload_{idx:03d}.json"
    out_path.write_text(json.dumps(payload, indent=2))
PY

python runtime/simulation/content_integrity_eval_harness.py \
  --input-dir "$TMP_DIR" \
  --manifest "$MANIFEST_PATH" \
  --output "$OUTPUT_PATH"
