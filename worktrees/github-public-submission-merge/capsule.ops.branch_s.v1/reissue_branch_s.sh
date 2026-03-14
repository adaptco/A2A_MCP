#!/usr/bin/env bash
set -euo pipefail

OUT=".out"
LEDGER="ledger.branch_s.jsonl"
REISSUE_HASH="reissue.sha256"
FEDERATION_RESP_PATTERN="dao.federation.relay"

mkdir -p "$OUT"

generate_id() {
  python - <<'PY'
import uuid
print(uuid.uuid4().hex)
PY
}

federate=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --federate)
      federate=true
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
LEDGER="ledger.branch_s.jsonl"
OUT_DIR=".out"
MANIFEST_TEMPLATE="manifest.json"
BEARER_TOKEN="${BEARER_TOKEN:-unset}"

mkdir -p "$OUT_DIR"

if [[ ! -f "$MANIFEST_TEMPLATE" ]]; then
  echo "Manifest template $MANIFEST_TEMPLATE not found" >&2
  exit 1
fi

federate=false
for arg in "$@"; do
  case "$arg" in
    --federate)
      federate=true
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

if [[ "$federate" == true && "${BEARER_TOKEN:-unset}" == "unset" ]]; then
  echo "BEARER_TOKEN is required for federation." >&2
  exit 1
fi

timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
epoch_commit=$(generate_id)

cat <<LOG
[${timestamp}] Sentinel reissue started.
 - Commit: ${epoch_commit}
 - Federation: ${federate}
LOG

cat <<EOF_LEDGER >> "$LEDGER"
{"timestamp":"${timestamp}","op":"reissue","commit":"${epoch_commit}","federated":${federate}}
EOF_LEDGER

cat <<EOF_JSON > "$OUT/capsule.reissue.receipt.v1.json"
{
  "type": "capsule.reissue.receipt.v1",
  "epoch": "sentinel-100",
  "commit": "${epoch_commit}",
  "reissued_at": "${timestamp}",
  "initiator": "council.node08",
  "annotations": {
    "phase": "attestation",
    "scrollstream_mode": "live"
  }
}
EOF_JSON

if [[ "$federate" == true ]]; then
  federation_receipt="$OUT/capsule.federation.receipt.v1.json"
  cat <<EOF_FED > "$federation_receipt"
{
  "type": "capsule.federation.receipt.v1",
  "epoch": "sentinel-100",
  "commit": "${epoch_commit}",
  "relayed_at": "${timestamp}",
  "relay_nodes": ["council.vault", "remix.constellation", "dao.licensing"],
  "bearer_token_present": true
}
EOF_FED

  cat <<EOF_RESP > "${FEDERATION_RESP_PATTERN}.${epoch_commit}.json"
{
  "status": "accepted",
  "epoch": "sentinel-100",
  "commit": "${epoch_commit}",
  "timestamp": "${timestamp}"
}
EOF_RESP

  sha256sum "$OUT/capsule.reissue.receipt.v1.json" "$federation_receipt" > "$REISSUE_HASH"
else
  sha256sum "$OUT/capsule.reissue.receipt.v1.json" > "$REISSUE_HASH"
fi

cat <<LOG
[${timestamp}] Sentinel reissue completed.
 - Ledger updated: ${LEDGER}
 - Receipt: ${OUT}/capsule.reissue.receipt.v1.json
 - Federation receipt: $([[ "$federate" == true ]] && echo "$OUT/capsule.federation.receipt.v1.json" || echo "n/a")
 - Hash archive: ${REISSUE_HASH}
LOG
if $federate && [[ "$BEARER_TOKEN" == "unset" || -z "$BEARER_TOKEN" ]]; then
  echo "BEARER_TOKEN must be set for federation" >&2
  exit 1
fi

timestamp=$(date -u +"%Y-%m-%dT%H-%M-%SZ")
manifest_out="$OUT_DIR/manifest.reissue.$timestamp.json"
cp "$MANIFEST_TEMPLATE" "$manifest_out"

action="reissue"
receipt_name="capsule.reissue.receipt.v1.$timestamp.json"
status="sentinel-epoch-reissued"
relay_payload=""

if $federate; then
  action="federate"
  receipt_name="capsule.federation.receipt.v1.$timestamp.json"
  status="sentinel-epoch-federated"
  relay_payload="$OUT_DIR/dao.federation.relay.$timestamp.json"
  cat > "$relay_payload" <<JSON
{
  "capsule": "capsule.ops.branch_s.v1",
  "timestamp": "$timestamp",
  "bearer_token_last4": "${BEARER_TOKEN: -4}",
  "status": "relay-prepared"
}
JSON
fi

gate_report="$OUT_DIR/gate_report.$action.$timestamp.json"
cat > "$gate_report" <<JSON
{
  "capsule": "capsule.ops.branch_s.v1",
  "action": "$action",
  "timestamp": "$timestamp",
  "status": "$status"
}
JSON

receipt="$OUT_DIR/$receipt_name"
{
  echo "{"
  echo "  \"capsule\": \"capsule.ops.branch_s.v1\","
  echo "  \"action\": \"$action\","
  echo "  \"timestamp\": \"$timestamp\","
  echo "  \"artifact_manifest\": \"$manifest_out\","
  echo "  \"gate_report\": \"$gate_report\""
  if [[ -n "$relay_payload" ]]; then
    echo "  ,\"relay_payload\": \"$relay_payload\""
  fi
  echo "}"
} > "$receipt"

if [[ -n "$relay_payload" ]]; then
  sha256sum "$manifest_out" "$gate_report" "$receipt" "$relay_payload" > reissue.sha256
else
  sha256sum "$manifest_out" "$gate_report" "$receipt" > reissue.sha256
fi

cat >> "$LEDGER" <<JSON
{"timestamp":"$timestamp","action":"$action","manifest":"$manifest_out","gate_report":"$gate_report","receipt":"$receipt"}
JSON

echo "${action^} receipt generated at $receipt"
echo "Ledger updated: $LEDGER"
