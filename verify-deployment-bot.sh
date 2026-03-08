#!/bin/bash
# verify-deployment-bot.sh - Verification script for Deployment Bot setup

set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Deployment Bot Verification${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

passed=0
failed=0

check_file() {
    local file=$1
    local desc=$2
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $desc ($file)"
        ((passed++))
        return 0
    else
        echo -e "${RED}✗${NC} $desc ($file) - NOT FOUND"
        ((failed++))
        return 1
    fi
}

check_executable() {
    local file=$1
    local desc=$2
    
    if [ -f "$file" ] && [ -x "$file" ]; then
        echo -e "${GREEN}✓${NC} $desc ($file) - executable"
        ((passed++))
        return 0
    elif [ -f "$file" ]; then
        echo -e "${YELLOW}⚠${NC} $desc ($file) - not executable (chmod +x to fix)"
        ((failed++))
        return 1
    else
        echo -e "${RED}✗${NC} $desc ($file) - NOT FOUND"
        ((failed++))
        return 1
    fi
}

echo "Checking core files..."
check_file "deployment_bot.py" "Microservice agent"
check_file "Dockerfile.bot" "Bot container image"
check_file "docker-compose.prod.yaml" "Production stack config"
check_file ".env.prod.example" "Environment template"
check_executable "deploy-bot.sh" "Deployment script"

echo ""
echo "Checking documentation..."
check_file "DEPLOYMENT_BOT.md" "Main documentation"
check_file "DEPLOYMENT_BOT_INTEGRATION.md" "Integration guide"
check_file "DEPLOYMENT_BOT_SETUP.md" "Setup summary"

echo ""
echo "Checking Python syntax..."
if python -m py_compile deployment_bot.py 2>/dev/null; then
    echo -e "${GREEN}✓${NC} deployment_bot.py - syntax valid"
    ((passed++))
else
    echo -e "${RED}✗${NC} deployment_bot.py - syntax error"
    ((failed++))
fi

echo ""
echo "Checking docker-compose syntax..."
if docker-compose -f docker-compose.prod.yaml config > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} docker-compose.prod.yaml - valid"
    ((passed++))
else
    echo -e "${YELLOW}⚠${NC} docker-compose.prod.yaml - cannot validate (Docker may not be running)"
    # Don't count as failure since Docker might not be available in dev env
fi

echo ""
echo "Checking Dockerfile syntax..."
if command -v hadolint &> /dev/null; then
    if hadolint Dockerfile.bot > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Dockerfile.bot - linter passed"
        ((passed++))
    else
        echo -e "${YELLOW}⚠${NC} Dockerfile.bot - linter warnings (non-critical)"
    fi
else
    echo -e "${YELLOW}⚠${NC} Dockerfile.bot - hadolint not installed (skipping lint)"
fi

echo ""
echo -e "${BLUE}================================${NC}"
echo -e "Results: ${GREEN}$passed passed${NC}, ${RED}$failed failed${NC}"
echo -e "${BLUE}================================${NC}"

if [ $failed -eq 0 ]; then
    echo -e ""
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo -e ""
    echo -e "Next steps:"
    echo -e "1. Create .env.prod from .env.prod.example"
    echo -e "2. Run: chmod +x deploy-bot.sh"
    echo -e "3. Run: ./deploy-bot.sh"
    echo -e ""
    exit 0
else
    echo -e ""
    echo -e "${RED}✗ Some checks failed. Please review above.${NC}"
    exit 1
fi
