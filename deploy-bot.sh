#!/bin/bash
# deploy-bot.sh - Automated Deployment Bot Deployment Script
# This script deploys the VH2 deployment bot microservice on a Linux VM

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yaml"
BOT_CONTAINER="vh2-deployment-bot-service"
BOT_IMAGE="vh2-deployment-bot:latest"
LOG_DIR="${PROJECT_DIR}/logs"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    log_success "Docker found: $(docker --version)"

    # Check docker-compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose is not installed"
        exit 1
    fi
    log_success "docker-compose found: $(docker-compose --version)"

    # Check Docker daemon
    if ! docker ps &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    log_success "Docker daemon is running"

    # Check if compose file exists
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    log_success "Compose file found: $COMPOSE_FILE"
}

load_env_file() {
    local env_file="${PROJECT_DIR}/.env.prod"

    if [ -f "$env_file" ]; then
        log_info "Loading environment from: $env_file"
        set -a
        source "$env_file"
        set +a
        log_success "Environment loaded"
    else
        log_warning "No .env.prod file found, using defaults"
        # Set defaults
        export DB_PASSWORD="${DB_PASSWORD:-prod-secret-change-me}"
        export DB_NAME="${DB_NAME:-mcp_db}"
        export DB_USER="${DB_USER:-postgres}"
        export RBAC_SECRET="${RBAC_SECRET:-prod-secret-change-me}"
        export LLM_MODEL="${LLM_MODEL:-gpt-4o-mini}"
    fi
}

create_log_dirs() {
    log_info "Creating log directories..."
    mkdir -p "$LOG_DIR/orchestrator"
    mkdir -p "$LOG_DIR/rbac"
    mkdir -p "$LOG_DIR/deployment_bot"
    chmod 755 "$LOG_DIR"
    log_success "Log directories created"
}

build_bot_image() {
    log_info "Building deployment bot image..."

    if docker build -f "${PROJECT_DIR}/Dockerfile.bot" -t "$BOT_IMAGE" "${PROJECT_DIR}"; then
        log_success "Bot image built: $BOT_IMAGE"
    else
        log_error "Failed to build bot image"
        exit 1
    fi
}

deploy_stack() {
    log_info "Deploying full stack with docker-compose..."

    if docker-compose -f "$COMPOSE_FILE" -p "vh2-stack" up -d; then
        log_success "Stack deployed successfully"
    else
        log_error "Failed to deploy stack"
        exit 1
    fi
}

wait_for_services() {
    log_info "Waiting for services to start..."
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        local running=$(docker-compose -f "$COMPOSE_FILE" -p "vh2-stack" ps -q | wc -l)
        local expected=4  # db, orchestrator, rbac, deployment-bot

        if [ "$running" -ge "$expected" ]; then
            log_success "All services are running"
            return 0
        fi

        log_info "Waiting for services... ($((attempt + 1))/$max_attempts)"
        sleep 2
        ((attempt++))
    done

    log_warning "Services did not start within expected time"
    return 1
}

show_status() {
    log_info "=== SERVICE STATUS ==="
    docker-compose -f "$COMPOSE_FILE" -p "vh2-stack" ps
    log_info "======================"
}

show_bot_logs() {
    log_info "Displaying deployment bot logs..."
    docker logs -f "$BOT_CONTAINER" &
    local pid=$!
    
    log_info "Bot logs streaming (press Ctrl+C to stop)..."
    wait $pid 2>/dev/null || true
}

cleanup_on_exit() {
    log_info "Deployment complete!"
    log_success "Deployment bot is running"
    log_info "To monitor bot logs: docker logs -f $BOT_CONTAINER"
    log_info "To check stack status: docker-compose -f $COMPOSE_FILE -p vh2-stack ps"
    log_info "To view all logs: tail -f $LOG_DIR/**/*.log"
}

main() {
    log_info "========================================="
    log_info "VH2 Deployment Bot - Automated Deploy"
    log_info "========================================="

    trap cleanup_on_exit EXIT

    check_prerequisites
    load_env_file
    create_log_dirs
    build_bot_image
    deploy_stack
    wait_for_services
    show_status

    log_success "Deployment Bot is ready!"
    log_info ""
    log_info "Next steps:"
    log_info "1. Check bot status:  docker logs -f $BOT_CONTAINER"
    log_info "2. View stack:        docker-compose -f $COMPOSE_FILE -p vh2-stack ps"
    log_info "3. Check logs:        tail -f $LOG_DIR/**/*.log"
}

# Run main
main "$@"
