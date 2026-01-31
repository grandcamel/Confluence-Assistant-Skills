#!/bin/bash
# E2E Test Runner for confluence-assistant-skills

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

USE_DOCKER=true
VERBOSE=${E2E_VERBOSE:-false}

while [[ $# -gt 0 ]]; do
    case $1 in
        --local) USE_DOCKER=false; shift ;;
        --verbose|-v) VERBOSE=true; export E2E_VERBOSE=true; shift ;;
        --shell)
            cd "$PROJECT_ROOT"
            docker compose -f docker/e2e/docker-compose.yml run --rm e2e-shell
            exit 0
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --local     Run locally without Docker"
            echo "  --shell     Open debug shell in Docker"
            echo "  --verbose   Verbose output"
            echo ""
            echo "Authentication (one required):"
            echo "  ANTHROPIC_API_KEY    Set env var with API key"
            echo "  claude auth login    OAuth via browser (creates ~/.claude/credentials.json)"
            exit 0
            ;;
        *) echo -e "${RED}Unknown: $1${NC}"; exit 1 ;;
    esac
done

# Check auth
check_authentication() {
    if [[ -n "$ANTHROPIC_API_KEY" ]]; then
        echo -e "${GREEN}✓ Authentication: API key configured${NC}"
        return 0
    elif [[ -f "$HOME/.claude/credentials.json" ]]; then
        echo -e "${GREEN}✓ Authentication: OAuth configured${NC}"
        return 0
    fi
    return 1
}

if ! check_authentication; then
    echo -e "${RED}✗ No authentication configured${NC}"
    echo ""
    echo "E2E tests require authentication to access Claude. Choose one option:"
    echo ""
    echo -e "${YELLOW}Option A: OAuth Login (Recommended for local development)${NC}"
    echo "  Run: claude auth login"
    echo "  This opens your browser for OAuth authentication and stores"
    echo "  credentials in ~/.claude/credentials.json"
    echo ""
    echo -e "${YELLOW}Option B: API Key${NC}"
    echo "  Set the ANTHROPIC_API_KEY environment variable:"
    echo "  export ANTHROPIC_API_KEY=\"sk-ant-...\""
    echo ""
    echo "For CI/CD environments, use Option B with a secret."
    echo "For local development, Option A is recommended."
    exit 1
fi

cd "$PROJECT_ROOT"
mkdir -p test-results/e2e

if [[ "$USE_DOCKER" == "true" ]]; then
    echo -e "${YELLOW}Running in Docker...${NC}"
    docker compose -f docker/e2e/docker-compose.yml build e2e-tests
    docker compose -f docker/e2e/docker-compose.yml run --rm e2e-tests
else
    echo -e "${YELLOW}Running locally...${NC}"
    pip install -q -r requirements-e2e.txt
    if [[ "$VERBOSE" == "true" ]]; then
        python -m pytest tests/e2e/ -v --e2e-verbose --tb=short
    else
        python -m pytest tests/e2e/ -v --tb=short
    fi
fi

echo -e "${GREEN}Results: test-results/e2e/${NC}"
