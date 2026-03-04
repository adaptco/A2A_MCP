#!/usr/bin/env bash
set -euo pipefail

# Telematics Agent Monitor (starter automation)
# Polls a telemetry endpoint and fans out actions to lightweight agent hooks.

readonly POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-30}"
readonly TELEMETRY_ENDPOINT="${TELEMETRY_ENDPOINT:-http://localhost:8080/api/telematics/events}"
readonly ALERT_THRESHOLD_SPEED="${ALERT_THRESHOLD_SPEED:-80}"
readonly LOG_FILE="${LOG_FILE:-./logs/telematics-agent-monitor.log}"
readonly STATE_FILE="${STATE_FILE:-./.telematics-monitor.state}"
readonly ENABLE_REMEDIATION="${ENABLE_REMEDIATION:-false}"

mkdir -p "$(dirname "$LOG_FILE")"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

log() {
  printf '%s | %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*" | tee -a "$LOG_FILE"
}

fetch_payload() {
  curl -fsS "$TELEMETRY_ENDPOINT"
}

last_processed_id() {
  [[ -f "$STATE_FILE" ]] && cat "$STATE_FILE" || echo ""
}

save_last_processed_id() {
  local event_id="$1"
  printf '%s' "$event_id" >"$STATE_FILE"
}

agent_detect_anomaly() {
  local event_json="$1"
  local speed
  speed="$(jq -r '.speed // 0' <<<"$event_json")"

  if (( speed > ALERT_THRESHOLD_SPEED )); then
    log "[anomaly-agent] event_id=$(jq -r '.id' <<<"$event_json") speed=${speed}mph above threshold=${ALERT_THRESHOLD_SPEED}mph"
    return 0
  fi

  return 1
}

agent_dispatch_alert() {
  local event_json="$1"
  local vehicle_id
  local speed
  vehicle_id="$(jq -r '.vehicle_id // "unknown"' <<<"$event_json")"
  speed="$(jq -r '.speed // "n/a"' <<<"$event_json")"

  log "[alert-agent] vehicle=${vehicle_id} speed=${speed} action=notify"
}

agent_remediate() {
  local event_json="$1"
  local vehicle_id
  vehicle_id="$(jq -r '.vehicle_id // "unknown"' <<<"$event_json")"

  if [[ "$ENABLE_REMEDIATION" == "true" ]]; then
    log "[remediation-agent] vehicle=${vehicle_id} action=throttle-request"
    # Add your remediation command here (example):
    # curl -fsS -X POST http://localhost:8080/api/vehicle/$vehicle_id/throttle
  else
    log "[remediation-agent] vehicle=${vehicle_id} skipped (ENABLE_REMEDIATION=false)"
  fi
}

process_events() {
  local payload="$1"
  local last_id
  last_id="$(last_processed_id)"

  jq -c '.events[]?' <<<"$payload" | while IFS= read -r event_json; do
    local event_id
    event_id="$(jq -r '.id' <<<"$event_json")"

    [[ -z "$event_id" || "$event_id" == "null" ]] && continue
    [[ -n "$last_id" && "$event_id" == "$last_id" ]] && continue

    log "[ingest-agent] processing event_id=${event_id}"

    if agent_detect_anomaly "$event_json"; then
      agent_dispatch_alert "$event_json"
      agent_remediate "$event_json"
    fi

    save_last_processed_id "$event_id"
  done
}

main() {
  require_cmd curl
  require_cmd jq

  log "telematics monitor started endpoint=${TELEMETRY_ENDPOINT} interval=${POLL_INTERVAL_SECONDS}s"

  while true; do
    if payload="$(fetch_payload)"; then
      process_events "$payload"
    else
      log "[ingest-agent] fetch failed endpoint=${TELEMETRY_ENDPOINT}"
    fi

    sleep "$POLL_INTERVAL_SECONDS"
  done
}

main "$@"
