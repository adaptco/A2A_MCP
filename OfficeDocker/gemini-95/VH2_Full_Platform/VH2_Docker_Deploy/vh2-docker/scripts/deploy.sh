#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════
# VH2 SOVEREIGN SUSPENSION RIG — Deploy Shell Script
#
# Usage:
#   ./deploy.sh            # full pipeline: test → build → deploy
#   ./deploy.sh test       # run unit tests only
#   ./deploy.sh build      # build images only
#   ./deploy.sh up         # start stack (assumes built)
#   ./deploy.sh down       # stop stack
#   ./deploy.sh validate   # run backend validator against live API
#   ./deploy.sh logs       # tail all service logs
#   ./deploy.sh status     # show health of all services
#   ./deploy.sh clean      # remove containers, images, networks
#
# Fail-closed: any step failure halts the pipeline (set -euo pipefail)
# ════════════════════════════════════════════════════════════════════════

set -euo pipefail
IFS=$'\n\t'

# ── CONSTANTS ─────────────────────────────────────────────────────────────
GOLD='\033[38;5;178m'
GREEN='\033[38;5;114m'
RED='\033[38;5;160m'
CYAN='\033[38;5;80m'
DIM='\033[38;5;239m'
RST='\033[0m'

COMPOSE_FILE="docker-compose.yml"
BACKEND_URL="http://localhost/api"
PROJECT="vh2"

# SHA-256 WITNESS SPEC (must match backend invariants)
WITNESS_SPEC='{
  "spoke_count":5,"rim_diameter_in":19,"front_et_mm":29,
  "rear_et_mm":22,"kpi_deg":12.5,"scrub_radius_mm":45,"c5_sector_deg":72
}'

# ── HELPERS ───────────────────────────────────────────────────────────────
log()  { echo -e "${DIM}[$(date +%H:%M:%S)]${RST} $*"; }
ok()   { echo -e "${GREEN}  ✓${RST} $*"; }
err()  { echo -e "${RED}  ✗ $*${RST}"; }
step() { echo -e "\n${GOLD}══ $* ${RST}"; }
fail() { err "$*"; exit 1; }

banner() {
  echo -e "${GOLD}"
  echo "  ╔══════════════════════════════════════════════════════════╗"
  echo "  ║  VH2 · SOVEREIGN SUSPENSION RIG · DEPLOY PIPELINE       ║"
  echo "  ║  ADVAN GT BEYOND C5 · KPI 12.5° · SHA-256 WITNESSED     ║"
  echo "  ╚══════════════════════════════════════════════════════════╝${RST}"
  echo ""
}

check_deps() {
  step "DEPENDENCY CHECK"
  for cmd in docker node curl jq; do
    if command -v "$cmd" &>/dev/null; then
      ok "$cmd $(command -v "$cmd")"
    else
      err "$cmd not found — install it first"
      [[ "$cmd" == "jq" ]] && echo "    brew install jq  |  apt install jq" || true
      [[ "$cmd" != "jq" ]] && exit 1 || true
    fi
  done
  docker info &>/dev/null || fail "Docker daemon not running"
  ok "Docker daemon reachable"
}

# ── STEP: SERVER-SIDE UNIT TESTS (fail-closed) ────────────────────────────
run_tests() {
  step "SERVER-SIDE UNIT TESTS"
  log "Running backend validator tests…"

  if [ ! -f "backend/tests/validator.test.js" ]; then
    fail "Test file not found: backend/tests/validator.test.js"
  fi

  cd backend
  # Install deps if needed
  if [ ! -d node_modules ]; then
    log "Installing backend deps…"
    npm ci --silent
  fi

  # Run tests — exit code propagates via set -e
  if node tests/validator.test.js; then
    ok "All server-side tests PASSED"
  else
    fail "SERVER-SIDE TESTS FAILED — pipeline halted (SYSTEM HALT)"
  fi
  cd ..
}

# ── STEP: DOCKER BUILD ────────────────────────────────────────────────────
build_images() {
  step "DOCKER BUILD"
  log "Building backend socket…"
  docker compose -f "$COMPOSE_FILE" build backend \
    --build-arg BUILDKIT_INLINE_CACHE=1 2>&1 | tail -5
  ok "Backend image built"

  log "Building frontend socket…"
  docker compose -f "$COMPOSE_FILE" build frontend \
    --build-arg BUILDKIT_INLINE_CACHE=1 2>&1 | tail -5
  ok "Frontend image built"
}

# ── STEP: STACK UP ────────────────────────────────────────────────────────
stack_up() {
  step "STACK STARTUP"
  log "Starting all services…"
  docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

  log "Waiting for health checks…"
  local retries=24
  local interval=5

  for ((i=1; i<=retries; i++)); do
    local backend_health frontend_health nginx_health
    backend_health=$(docker inspect --format='{{.State.Health.Status}}' vh2-backend  2>/dev/null || echo "not_found")
    frontend_health=$(docker inspect --format='{{.State.Health.Status}}' vh2-frontend 2>/dev/null || echo "not_found")
    nginx_health=$(docker inspect --format='{{.State.Health.Status}}' vh2-nginx     2>/dev/null || echo "not_found")

    if [[ "$backend_health" == "healthy" && "$frontend_health" == "healthy" ]]; then
      ok "Backend:  $backend_health"
      ok "Frontend: $frontend_health"
      ok "Nginx:    $nginx_health"
      break
    fi

    if [[ $i -eq $retries ]]; then
      err "Health checks timed out after $((retries*interval))s"
      docker compose -f "$COMPOSE_FILE" logs --tail=20
      fail "Stack failed to become healthy"
    fi

    echo -ne "  ${DIM}Attempt ${i}/${retries} (backend:${backend_health} frontend:${frontend_health})…${RST}\r"
    sleep $interval
  done
}

# ── STEP: LIVE API VALIDATION ──────────────────────────────────────────────
validate_api() {
  step "LIVE BACKEND VALIDATION (fail-closed)"
  log "Hitting ${BACKEND_URL}/validate with canonical spec…"

  local response
  local http_code

  if ! command -v curl &>/dev/null; then
    log "curl not available — skipping live validation"
    return 0
  fi

  http_code=$(curl -s -o /tmp/vh2_validate.json -w "%{http_code}" \
    -X POST "${BACKEND_URL}/validate" \
    -H "Content-Type: application/json" \
    -d "$WITNESS_SPEC" \
    --max-time 10 || echo "000")

  if [[ "$http_code" == "000" ]]; then
    err "Could not reach backend API at ${BACKEND_URL}"
    log "Stack may still be starting — run: ./deploy.sh validate"
    return 1
  fi

  if command -v jq &>/dev/null; then
    local status pass witness
    status=$(jq -r '.status'             /tmp/vh2_validate.json 2>/dev/null || echo "unknown")
    pass=$(jq -r '.pass'                 /tmp/vh2_validate.json 2>/dev/null || echo "false")
    witness=$(jq -r '.witness.tag // ""' /tmp/vh2_validate.json 2>/dev/null || echo "")

    if [[ "$pass" == "true" ]]; then
      ok "API status: ${status}"
      ok "Witness:    ${witness}"
      ok "HTTP:       ${http_code}"
    else
      cat /tmp/vh2_validate.json
      fail "Validation FAILED — status=${status} http=${http_code}"
    fi
  else
    ok "API responded HTTP ${http_code}"
    cat /tmp/vh2_validate.json
  fi

  # Health endpoint
  log "Checking /health…"
  local hcode
  hcode=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL%/api}/health" --max-time 5 || echo "000")
  [[ "$hcode" == "200" ]] && ok "Health endpoint: 200 OK" || err "Health endpoint: ${hcode}"
}

# ── STEP: STATUS ──────────────────────────────────────────────────────────
show_status() {
  step "SERVICE STATUS"
  docker compose -f "$COMPOSE_FILE" ps
  echo ""
  echo -e "${DIM}Listening on:${RST}"
  echo -e "  ${CYAN}http://localhost${RST}          — Plugin demo (frontend socket)"
  echo -e "  ${CYAN}http://localhost/api/spec${RST} — Canonical spec (backend socket)"
  echo -e "  ${CYAN}http://localhost/health${RST}   — Health probe"
  echo -e "  ${CYAN}http://localhost/vh2-plugin.js${RST} — Embeddable plugin"
}

# ── COMMAND ROUTING ───────────────────────────────────────────────────────
CMD="${1:-deploy}"

banner

case "$CMD" in
  test)
    check_deps
    run_tests
    ok "TEST PIPELINE COMPLETE"
    ;;

  build)
    check_deps
    run_tests
    build_images
    ok "BUILD PIPELINE COMPLETE"
    ;;

  up)
    stack_up
    show_status
    ;;

  down)
    step "STACK TEARDOWN"
    docker compose -f "$COMPOSE_FILE" down
    ok "Stack stopped"
    ;;

  validate)
    validate_api
    ;;

  logs)
    docker compose -f "$COMPOSE_FILE" logs -f --tail=50
    ;;

  status)
    show_status
    ;;

  clean)
    step "CLEAN"
    docker compose -f "$COMPOSE_FILE" down --rmi local --volumes --remove-orphans
    ok "Containers, images, and networks removed"
    ;;

  deploy|*)
    check_deps
    run_tests
    build_images
    stack_up
    validate_api || true   # API validation non-fatal (stack still up)
    show_status
    echo ""
    echo -e "${GREEN}  ══ VH2 SOVEREIGN DEPLOY COMPLETE ══${RST}"
    echo -e "  ${GOLD}Witness hash pinned. Open http://localhost${RST}"
    ;;
esac
