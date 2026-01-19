#!/usr/bin/env bash
# Run live integration tests for each skill separately to avoid namespace conflicts
# Requires Confluence credentials: CONFLUENCE_API_TOKEN, CONFLUENCE_EMAIL, CONFLUENCE_SITE_URL
#
# Usage:
#   ./scripts/run_live_tests.sh              # Run all live tests
#   ./scripts/run_live_tests.sh --verbose    # Run with verbose output
#   ./scripts/run_live_tests.sh --skill confluence-page  # Run specific skill only
#   ./scripts/run_live_tests.sh --space-key MYTEST       # Use existing space
#   ./scripts/run_live_tests.sh --keep-space             # Don't delete test space

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SKILLS_ROOT="$PROJECT_ROOT/skills"

# All skills to test
ALL_SKILLS=(
    "confluence-analytics"
    "confluence-attachment"
    "confluence-comment"
    "confluence-hierarchy"
    "confluence-jira"
    "confluence-label"
    "confluence-page"
    "confluence-permission"
    "confluence-property"
    "confluence-search"
    "confluence-space"
    "confluence-template"
    "confluence-watch"
    "shared"
)

# Parse arguments
VERBOSE=""
SPECIFIC_SKILL=""
SPACE_KEY=""
KEEP_SPACE=""
EXTRA_ARGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -s|--skill)
            SPECIFIC_SKILL="$2"
            shift 2
            ;;
        --space-key)
            SPACE_KEY="$2"
            shift 2
            ;;
        --keep-space)
            KEEP_SPACE="--keep-space"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Run live integration tests against real Confluence."
            echo ""
            echo "Options:"
            echo "  -v, --verbose         Show verbose test output"
            echo "  -s, --skill NAME      Run tests for specific skill only"
            echo "  --space-key KEY       Use existing space instead of creating temporary one"
            echo "  --keep-space          Keep test space after tests (for debugging)"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Required environment variables:"
            echo "  CONFLUENCE_SITE_URL   - Confluence site URL (e.g., https://your-site.atlassian.net)"
            echo "  CONFLUENCE_EMAIL      - Atlassian account email"
            echo "  CONFLUENCE_API_TOKEN  - API token from id.atlassian.com"
            echo ""
            echo "Available skills:"
            for skill in "${ALL_SKILLS[@]}"; do
                echo "  - $skill"
            done
            exit 0
            ;;
        *)
            # Pass unknown args to pytest
            EXTRA_ARGS="$EXTRA_ARGS $1"
            shift
            ;;
    esac
done

# Check for credentials
if [[ -z "${CONFLUENCE_API_TOKEN:-}" ]] || [[ -z "${CONFLUENCE_EMAIL:-}" ]] || [[ -z "${CONFLUENCE_SITE_URL:-}" ]]; then
    echo -e "${RED}ERROR: Missing Confluence credentials${NC}"
    echo ""
    echo "Required environment variables:"
    echo "  CONFLUENCE_SITE_URL   - Confluence site URL (e.g., https://your-site.atlassian.net)"
    echo "  CONFLUENCE_EMAIL      - Atlassian account email"
    echo "  CONFLUENCE_API_TOKEN  - API token from id.atlassian.com"
    echo ""
    echo "Get your API token from: https://id.atlassian.com/manage-profile/security/api-tokens"
    exit 1
fi

# Determine which skills to test
if [[ -n "$SPECIFIC_SKILL" ]]; then
    SKILLS=("$SPECIFIC_SKILL")
else
    SKILLS=("${ALL_SKILLS[@]}")
fi

# Results tracking
declare -A SKILL_RESULTS
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0
FAILED_SKILLS=()

# Print header
echo ""
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Live Integration Tests - Confluence Assistant Skills${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Confluence Site:${NC} $CONFLUENCE_SITE_URL"
echo -e "${YELLOW}Email:${NC} $CONFLUENCE_EMAIL"
if [[ -n "$SPACE_KEY" ]]; then
    echo -e "${YELLOW}Test Space:${NC} $SPACE_KEY (existing)"
fi
if [[ -n "$KEEP_SPACE" ]]; then
    echo -e "${YELLOW}Keep Space:${NC} Yes (for debugging)"
fi
echo ""

# Run tests for each skill
for skill in "${SKILLS[@]}"; do
    echo -e "${YELLOW}Testing:${NC} $skill"

    TEST_PATH="$SKILLS_ROOT/$skill/tests/live_integration"

    if [[ ! -d "$TEST_PATH" ]]; then
        echo -e "  ${YELLOW}⊘ SKIPPED${NC} (no live_integration directory)"
        SKILL_RESULTS[$skill]="SKIP"
        ((TOTAL_SKIPPED++))
        continue
    fi

    # Check for test files
    test_count=$(find "$TEST_PATH" -name "test_*.py" 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$test_count" -eq 0 ]]; then
        echo -e "  ${YELLOW}⊘ SKIPPED${NC} (no test files)"
        SKILL_RESULTS[$skill]="SKIP"
        ((TOTAL_SKIPPED++))
        continue
    fi

    # Build pytest command
    PYTEST_CMD="python -m pytest $TEST_PATH --live"

    if [[ -n "$VERBOSE" ]]; then
        PYTEST_CMD="$PYTEST_CMD -v"
    fi

    if [[ -n "$SPACE_KEY" ]]; then
        PYTEST_CMD="$PYTEST_CMD --space-key=$SPACE_KEY"
    fi

    if [[ -n "$KEEP_SPACE" ]]; then
        PYTEST_CMD="$PYTEST_CMD $KEEP_SPACE"
    fi

    if [[ -n "$EXTRA_ARGS" ]]; then
        PYTEST_CMD="$PYTEST_CMD $EXTRA_ARGS"
    fi

    # Run tests
    if eval $PYTEST_CMD; then
        echo -e "  ${GREEN}✓ PASSED${NC}"
        SKILL_RESULTS[$skill]="PASS"
        ((TOTAL_PASSED++))
    else
        echo -e "  ${RED}✗ FAILED${NC}"
        SKILL_RESULTS[$skill]="FAIL"
        FAILED_SKILLS+=("$skill")
        ((TOTAL_FAILED++))
    fi
done

# Print summary
echo ""
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Summary${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
echo ""

# Results table
printf "%-25s %10s\n" "Skill" "Status"
printf "%-25s %10s\n" "─────────────────────────" "──────────"

for skill in "${SKILLS[@]}"; do
    status="${SKILL_RESULTS[$skill]:-SKIP}"

    case $status in
        PASS)
            printf "%-25s ${GREEN}%10s${NC}\n" "$skill" "PASS"
            ;;
        FAIL)
            printf "%-25s ${RED}%10s${NC}\n" "$skill" "FAIL"
            ;;
        SKIP)
            printf "%-25s ${YELLOW}%10s${NC}\n" "$skill" "SKIP"
            ;;
    esac
done

printf "%-25s %10s\n" "─────────────────────────" "──────────"
printf "%-25s %10s\n" "Passed" "$TOTAL_PASSED"
printf "%-25s %10s\n" "Failed" "$TOTAL_FAILED"
printf "%-25s %10s\n" "Skipped" "$TOTAL_SKIPPED"

echo ""

# Exit status
if [[ ${#FAILED_SKILLS[@]} -gt 0 ]]; then
    echo -e "${RED}Failed skills:${NC}"
    for skill in "${FAILED_SKILLS[@]}"; do
        echo "  - $skill"
    done
    echo ""
    echo -e "${RED}Live integration tests failed.${NC}"
    exit 1
else
    echo -e "${GREEN}All live integration tests passed!${NC}"
fi

exit 0
