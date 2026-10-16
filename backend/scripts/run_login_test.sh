#!/bin/bash
#
# Run Selenium login test that verifies dashboard access
# Fetches password from Vault automatically
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                        ║${NC}"
echo -e "${BLUE}║         Selenium Login & Dashboard Test            ║${NC}"
echo -e "${BLUE}║                                                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if Vault is running
echo -e "${YELLOW}[1/4] Checking Vault...${NC}"
if ! docker ps --format '{{.Names}}' | grep -q "^vault$"; then
    echo -e "${YELLOW}⚠️  Vault container not running, starting it...${NC}"
    docker-compose -f docker-compose.dev.yml up -d vault
    sleep 3
fi

# Verify Vault is accessible
VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-sentinelgrid-dev-root-token}"

if curl -s -f "$VAULT_ADDR/v1/sys/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Vault is accessible${NC}"
else
    echo -e "${YELLOW}⚠️  Vault may not be ready, but continuing...${NC}"
fi

# Check if frontend is running
echo -e "${YELLOW}[2/4] Checking frontend...${NC}"
FRONTEND_URL="${WEBSITE_URL:-https://localhost:3443}"
if curl -k -s -f "$FRONTEND_URL" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend is accessible${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend may not be running at $FRONTEND_URL${NC}"
    echo -e "${YELLOW}   Start it with: docker-compose -f docker-compose.dev.yml up -d frontend${NC}"
fi

# Set environment variables for test
export VAULT_ADDR="$VAULT_ADDR"
export VAULT_TOKEN="$VAULT_TOKEN"
export WEBSITE_URL="${WEBSITE_URL:-https://localhost:3443}"
export TEST_USERNAME="${TEST_USERNAME:-admin@sentinelgrid.ai}"

# Run the test
echo -e "${YELLOW}[3/4] Running Selenium login test...${NC}"
echo -e "${BLUE}   Test: test_simple_login_to_dashboard${NC}"
echo -e "${BLUE}   Email: $TEST_USERNAME${NC}"
echo -e "${BLUE}   Password: (fetched from Vault)${NC}"
echo -e "${BLUE}   Environment: conda (test)${NC}"
echo ""

# Activate conda environment and run pytest
# Use conda run to execute in the test environment
conda run -n test pytest backend/tests/test_auth_selenium.py::TestSimpleLogin::test_simple_login_to_dashboard \
    -v -s \
    --tb=short \
    -W ignore::DeprecationWarning

TEST_EXIT_CODE=$?

echo ""
echo -e "${YELLOW}[4/4] Test Results${NC}"
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Login test passed! Dashboard is accessible.${NC}"
else
    echo -e "${YELLOW}⚠️  Test failed (exit code: $TEST_EXIT_CODE)${NC}"
    echo -e "${YELLOW}   Check the output above for details${NC}"
fi

exit $TEST_EXIT_CODE

