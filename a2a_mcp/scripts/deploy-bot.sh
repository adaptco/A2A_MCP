#!/bin/bash
# scripts/deploy-bot.sh — A2A_MCP Digital Twin Deployment Bot Bootstrap
# Deploys the full twin stack governed by the DeploymentBot microservice.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.twin.yml"
PROJECT_NAME="a2a-twin"
BOT_CONTAINER="a2a-twin-deployment-bot"
LOG_DIR="${PROJECT_DIR}/logs"
EXPECTED_SERVICES=4   # db, redis, orchestrator, agent-mesh, deployment-bot

log_info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $*"; }

check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v docker &>/dev/null; then
        log_error "Docker is not installed"; exit 1
    fi
    log_success "Docker: $(docker --version)"

    if ! docker ps &>/dev/null; then
        log_error "Docker daemon is not running"; exit 1
    fi
    log_success "Docker daemon running"

    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Compose file not found: $COMPOSE_FILE"; exit 1
    fi
    log_success "Compose file: $COMPOSE_FILE"
}

load_env_file() {
    local env_file="${PROJECT_DIR}/.env.twin"
    if [ -f "$env_file" ]; then
        log_info "Loading environment from: $env_file"
        set -a; source "$env_file"; set +a
        log_success "Environment loaded"
    else
        log_warning "No .env.twin found — using defaults. Copy .env.twin.example to get started."
        export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-twin-pass-change-me}"
        export POSTGRES_DB="${POSTGRES_DB:-a2a_twin}"
        export GEMINI_API_KEY="${GEMINI_API_KEY:-}"
        export HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-30}"
    fi
}

create_log_dirs() {
    log_info "Creating log directories..."
    mkdir -p "${LOG_DIR}/deployment_bot"
    chmod 755 "${LOG_DIR}"
    log_success "Log directories ready"
}

deploy_stack() {
    log_info "Building and deploying Digital Twin stack..."
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d --build
    log_success "Stack deployed"
}

wait_for_services() {
    log_info "Waiting for services to start..."
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        local running
        running=$(docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps -q 2>/dev/null | wc -l)

        if [ "$running" -ge "$EXPECTED_SERVICES" ]; then
            log_success "All $EXPECTED_SERVICES services running"
            return 0
        fi

        log_info "Waiting... ($((attempt + 1))/$max_attempts) — $running/$EXPECTED_SERVICES up"
        sleep 3
        ((attempt++))
    done

    log_warning "Services did not all start within expected time — check 'docker compose ps'"
    return 1
}

show_status() {
    log_info "=== TWIN STACK STATUS ==="
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps
    log_info "========================="
}

cleanup_on_exit() {
    log_success "Deployment complete!"
    log_info "Monitor bot logs:  docker logs -f $BOT_CONTAINER"
    log_info "Stack status:      docker compose -f $COMPOSE_FILE -p $PROJECT_NAME ps"
    log_info "All logs:          tail -f $LOG_DIR/deployment_bot/*.log"
}

main() {
    log_info "================================================="
    log_info "  A2A_MCP Digital Twin — Deployment Bot Deploy  "
    log_info "================================================="

    trap cleanup_on_exit EXIT

    check_prerequisites
    load_env_file
    create_log_dirs
    deploy_stack
    wait_for_services
    show_status

    log_success "Deployment Bot is now governing the Digital Twin stack!"
}

main "$@"
