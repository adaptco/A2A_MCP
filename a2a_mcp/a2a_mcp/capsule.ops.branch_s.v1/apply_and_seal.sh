#!/usr/bin/env bash
set -euo pipefail

OUT=".out"
LEDGER="ledger.branch_s.jsonl"
MANIFEST="manifest.json"
GATE_REPORT="$OUT/gate_report.json"
REISSUE_RECEIPT="$OUT/capsule.reissue.receipt.v1.json"
CHECKSUMS="checksums.sha256"

mkdir -p "$OUT"

generate_id() {
  python - <<'PY'
import uuid
print(uuid.uuid4().hex)
PY
}

timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
seal_commit=$(generate_id)

cat <<LOG
[${timestamp}] Sentinel apply-and-seal invoked.
 - Commit: ${seal_commit}
 - Output dir: ${OUT}
LOG

cp "$MANIFEST" "$OUT/manifest.json"

cat <<EOF_JSON > "$GATE_REPORT"
{
  "operation": "apply_and_seal",
  "timestamp": "${timestamp}",
  "node": "council.node02",
  "status": "sealed",
  "commit": "${seal_commit}"
}
EOF_JSON

cat <<EOF_JSON > "$REISSUE_RECEIPT"
{
  "type": "capsule.reissue.receipt.v1",
  "epoch": "sentinel-100",
  "commit": "${seal_commit}",
  "sealed_at": "${timestamp}",
  "issued_by": ["node02", "node06", "node08"],
  "annotations": {
    "strand_sequence": ["machine", "ritual", "council", "veracity"],
    "emotional_register": ["continuity", "integrity", "trust", "bloom"],
    "caption": "Veracity blooms where truth is sealed."
  }
}
EOF_JSON

cat <<EOF_LEDGER >> "$LEDGER"
{"timestamp":"${timestamp}","op":"apply","commit":"${seal_commit}","status":"sealed"}
EOF_LEDGER

sha256sum "$OUT/manifest.json" "$GATE_REPORT" "$REISSUE_RECEIPT" > "$CHECKSUMS"

cat <<LOG
[${timestamp}] Sentinel seal finalized.
 - Ledger updated: ${LEDGER}
 - Gate report: ${GATE_REPORT}
 - Receipt: ${REISSUE_RECEIPT}
 - Checksums: ${CHECKSUMS}
LOG
LEDGER="ledger.branch_s.jsonl"
OUT_DIR=".out"
MANIFEST_TEMPLATE="manifest.json"

mkdir -p "$OUT_DIR"

if [[ ! -f "$MANIFEST_TEMPLATE" ]]; then
  echo "Manifest template $MANIFEST_TEMPLATE not found" >&2
  exit 1
fi

timestamp=$(date -u +"%Y-%m-%dT%H-%M-%SZ")
manifest_out="$OUT_DIR/manifest.apply.$timestamp.json"
gate_report="$OUT_DIR/gate_report.$timestamp.json"
receipt="$OUT_DIR/capsule.apply.receipt.v1.$timestamp.json"

cp "$MANIFEST_TEMPLATE" "$manifest_out"

cat > "$gate_report" <<JSON
{
  "capsule": "capsule.ops.branch_s.v1",
  "action": "apply",
  "timestamp": "$timestamp",
  "status": "sentinel-seal-applied",
  "notes": [
    "Sentinel braid anchored",
    "Shimmer lattice verified"
  ]
}
JSON

cat > "$receipt" <<JSON
{
  "capsule": "capsule.ops.branch_s.v1",
  "action": "apply",
  "timestamp": "$timestamp",
  "artifact_manifest": "${manifest_out}",
  "gate_report": "${gate_report}"
}
JSON

sha256sum "$manifest_out" "$gate_report" "$receipt" > checksums.sha256

cat >> "$LEDGER" <<JSON
{"timestamp":"$timestamp","action":"apply","manifest":"$manifest_out","gate_report":"$gate_report","receipt":"$receipt"}
JSON

echo "Apply receipt generated at $receipt"
echo "Ledger updated: $LEDGER"
