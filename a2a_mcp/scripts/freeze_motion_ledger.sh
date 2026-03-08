#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CANON_SCRIPT="${ROOT_DIR}/scripts/canonicalize_manifest.py"
OUTPUT_DIR="${ROOT_DIR}/runtime"
LEDGER_PATH="${OUTPUT_DIR}/scrollstream_ledger.jsonl"
HUD_PATH="${OUTPUT_DIR}/hud_events.jsonl"

MOTION_CAPSULE="${ROOT_DIR}/capsules/motion/capsule.motion.ledger.v2.json"
REPLAY_CAPSULE="${ROOT_DIR}/capsules/replay/capsule.replay.token.v2.json"
ECHO_CAPSULE="${ROOT_DIR}/capsules/echo/capsule.echo.scrollstream.v2.json"

MOTION_CANONICAL="${OUTPUT_DIR}/capsule.motion.ledger.v2.canonical.json"
MOTION_SEALED="${OUTPUT_DIR}/capsule.motion.ledger.v2.sealed.json"
MOTION_HASH_PATH="${OUTPUT_DIR}/capsule.motion.ledger.v2.sha256"

REPLAY_CANONICAL="${OUTPUT_DIR}/capsule.replay.token.v2.canonical.json"
REPLAY_SEALED="${OUTPUT_DIR}/capsule.replay.token.v2.sealed.json"
REPLAY_HASH_PATH="${OUTPUT_DIR}/capsule.replay.token.v2.sha256"

ECHO_CANONICAL="${OUTPUT_DIR}/capsule.echo.scrollstream.v2.canonical.json"
ECHO_SEALED="${OUTPUT_DIR}/capsule.echo.scrollstream.v2.sealed.json"
ECHO_HASH_PATH="${OUTPUT_DIR}/capsule.echo.scrollstream.v2.sha256"

MAKER_SIGNATURE=""
CHECKER_SIGNATURE=""
HUD_EVENT="hud.motion.ledger.finalized"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --maker-signature)
      MAKER_SIGNATURE="${2:-}"
      shift 2
      ;;
    --checker-signature)
      CHECKER_SIGNATURE="${2:-}"
      shift 2
      ;;
    --hud-event)
      HUD_EVENT="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "${MAKER_SIGNATURE}" || -z "${CHECKER_SIGNATURE}" ]]; then
  echo "Both --maker-signature and --checker-signature are required." >&2
  exit 1
fi

if [[ "${MAKER_SIGNATURE}" == "${CHECKER_SIGNATURE}" ]]; then
  echo "Maker and checker signatures must be distinct." >&2
  exit 1
fi

for dep in jq python3 sha256sum; do
  if ! command -v "$dep" >/dev/null 2>&1; then
    echo "Required dependency '$dep' not found in PATH." >&2
    exit 1
  fi
done

for capsule in "${MOTION_CAPSULE}" "${REPLAY_CAPSULE}" "${ECHO_CAPSULE}"; do
  if [[ ! -f "${capsule}" ]]; then
    echo "Capsule not found: ${capsule}" >&2
    exit 1
  fi
done

if [[ ! -f "${CANON_SCRIPT}" ]]; then
  echo "Canonicalization script not found at ${CANON_SCRIPT}" >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"

python3 "${CANON_SCRIPT}" < "${MOTION_CAPSULE}" > "${MOTION_CANONICAL}"
MOTION_HASH=$(sha256sum "${MOTION_CANONICAL}" | cut -d' ' -f1)
printf "%s" "${MOTION_HASH}" > "${MOTION_HASH_PATH}"
MOTION_DIGEST="sha256:${MOTION_HASH}"

python3 "${CANON_SCRIPT}" < "${REPLAY_CAPSULE}" > "${REPLAY_CANONICAL}"
REPLAY_HASH=$(sha256sum "${REPLAY_CANONICAL}" | cut -d' ' -f1)
printf "%s" "${REPLAY_HASH}" > "${REPLAY_HASH_PATH}"
REPLAY_DIGEST="sha256:${REPLAY_HASH}"

python3 "${CANON_SCRIPT}" < "${ECHO_CAPSULE}" > "${ECHO_CANONICAL}"
ECHO_HASH=$(sha256sum "${ECHO_CANONICAL}" | cut -d' ' -f1)
printf "%s" "${ECHO_HASH}" > "${ECHO_HASH_PATH}"
ECHO_DIGEST="sha256:${ECHO_HASH}"

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

jq -S \
  --arg ts "${TIMESTAMP}" \
  --arg digest "${MOTION_DIGEST}" \
  --arg maker "${MAKER_SIGNATURE}" \
  --arg checker "${CHECKER_SIGNATURE}" \
  '
    .attestation = (.attestation // {}) |
    .attestation.status = "FOSSILIZED" |
    .attestation.sealed_by = "Council" |
    .attestation.sealed_at = $ts |
    .attestation.content_hash = $digest |
    .status = "SEALED" |
    .scrollstream.digest = $digest |
    .governance.signatures.maker = $maker |
    .governance.signatures.checker = $checker
  ' "${MOTION_CAPSULE}" > "${MOTION_SEALED}"

jq -S \
  --arg ts "${TIMESTAMP}" \
  --arg digest "${REPLAY_DIGEST}" \
  --arg ledger "${MOTION_DIGEST}" \
  --arg maker "${MAKER_SIGNATURE}" \
  --arg checker "${CHECKER_SIGNATURE}" \
  '
    .ledger_ref.digest = $ledger |
    .attestation = (.attestation // {}) |
    .attestation.status = "FOSSILIZED" |
    .attestation.sealed_by = "Council" |
    .attestation.sealed_at = $ts |
    .attestation.content_hash = $digest |
    .status = "SEALED" |
    .governance.signatures = [$maker, $checker]
  ' "${REPLAY_CAPSULE}" > "${REPLAY_SEALED}"

jq -S \
  --arg ts "${TIMESTAMP}" \
  --arg digest "${ECHO_DIGEST}" \
  --arg ledger "${MOTION_DIGEST}" \
  '
    .source.digest = $ledger |
    .attestation = (.attestation // {}) |
    .attestation.status = "FOSSILIZED" |
    .attestation.sealed_by = "Council" |
    .attestation.sealed_at = $ts |
    .attestation.content_hash = $digest |
    .status = "SEALED"
  ' "${ECHO_CAPSULE}" > "${ECHO_SEALED}"

export LEDGER_TIMESTAMP="${TIMESTAMP}"
export LEDGER_PATH HUD_PATH
export MOTION_DIGEST REPLAY_DIGEST ECHO_DIGEST MAKER_SIGNATURE CHECKER_SIGNATURE HUD_EVENT
python3 - <<'PY'
import json
import os
import sys

timestamp = os.environ["LEDGER_TIMESTAMP"]
motion_digest = os.environ["MOTION_DIGEST"]
replay_digest = os.environ["REPLAY_DIGEST"]
echo_digest = os.environ["ECHO_DIGEST"]
maker = os.environ["MAKER_SIGNATURE"]
checker = os.environ["CHECKER_SIGNATURE"]
hud_event = os.environ["HUD_EVENT"]

entries = [
    {
        "timestamp": timestamp,
        "event": "capsule.commit.v2",
        "capsule": "capsule.motion.ledger.v2",
        "digest": motion_digest,
        "maker_signature": maker,
        "sealed_by": "Council"
    },
    {
        "timestamp": timestamp,
        "event": "capsule.review.v2",
        "capsule": "capsule.motion.ledger.v2",
        "digest": motion_digest,
        "checker_signature": checker,
        "sealed_by": "Council"
    },
    {
        "timestamp": timestamp,
        "event": "capsule.seal.v2",
        "capsule": "capsule.motion.ledger.v2",
        "digest": motion_digest,
        "signatures": [maker, checker],
        "sealed_by": "Council"
    },
    {
        "timestamp": timestamp,
        "event": "motion.ledger.freeze.v2",
        "capsule": "capsule.motion.ledger.v2",
        "digest": motion_digest,
        "hud_event": hud_event
    },
    {
        "timestamp": timestamp,
        "event": "capsule.replay.token.issue.v2",
        "capsule": "capsule.replay.token.v2",
        "digest": replay_digest,
        "motion_ledger_digest": motion_digest,
        "signatures": [maker, checker]
    },
    {
        "timestamp": timestamp,
        "event": "scrollstream.echo.inscribe.v2",
        "capsule": "capsule.echo.scrollstream.v2",
        "digest": echo_digest,
        "source_capsule": "capsule.motion.ledger.v2"
    }
]

ledger_path = os.environ["LEDGER_PATH"]
with open(ledger_path, "a", encoding="utf-8") as handle:
    for entry in entries:
        json.dump(entry, handle, ensure_ascii=False)
        handle.write("\n")

hud_path = os.environ["HUD_PATH"]
if hud_path:
    hud_entry = {
        "timestamp": timestamp,
        "event": hud_event,
        "capsule": "capsule.motion.ledger.v2",
        "overlays": ["glyph.pulse", "aura.gold", "qlock.tick"],
        "emotion_arc": ["curiosity", "intimacy", "clarity", "wisdom"]
    }
    with open(hud_path, "a", encoding="utf-8") as handle:
        json.dump(hud_entry, handle, ensure_ascii=False)
        handle.write("\n")
PY

unset LEDGER_TIMESTAMP MOTION_DIGEST REPLAY_DIGEST ECHO_DIGEST MAKER_SIGNATURE CHECKER_SIGNATURE HUD_EVENT

printf "Motion ledger canonical written to %s\n" "${MOTION_CANONICAL}"
printf "Motion ledger sealed capsule written to %s\n" "${MOTION_SEALED}"
printf "Replay token sealed capsule written to %s\n" "${REPLAY_SEALED}"
printf "Echo capsule sealed capsule written to %s\n" "${ECHO_SEALED}"
printf "Ledger updated at %s\n" "${LEDGER_PATH}"
printf "HUD overlay logged at %s\n" "${HUD_PATH}"
