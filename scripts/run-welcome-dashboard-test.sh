#!/bin/bash

# Script to build frontend without cache and run welcome dashboard Selenium test
# Usage: ./scripts/run-welcome-dashboard-test.sh

set -e

echo "=========================================="
echo "Welcome Dashboard E2E Test Runner"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo -e "${YELLOW}Step 1: Building frontend without cache...${NC}"
cd "$FRONTEND_DIR"

# Build without cache using npm script
echo "  Building Next.js application (no cache)..."
npm run build:no-cache 2>&1 | tee /tmp/frontend-build.log

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo -e "${RED}❌ Frontend build failed!${NC}"
    echo "Check /tmp/frontend-build.log for details"
    exit 1
fi

echo -e "${GREEN}✅ Frontend built successfully${NC}"
echo ""

# Check if frontend is running
echo -e "${YELLOW}Step 2: Checking if frontend is running...${NC}"
FRONTEND_URL="${WEBSITE_URL:-https://localhost:3443}"

# Try to check if frontend is accessible (optional check)
if command -v curl &> /dev/null; then
    echo "  Checking if frontend is accessible at $FRONTEND_URL..."
    if curl -k -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" | grep -q "200\|301\|302"; then
        echo -e "${GREEN}✅ Frontend is accessible${NC}"
    else
        echo -e "${YELLOW}⚠️  Frontend may not be running. Make sure services are up.${NC}"
        echo "  Run: docker-compose -f docker-compose.dev.yml up"
    fi
else
    echo "  curl not available, skipping connectivity check"
fi
echo ""

# Run the test
echo -e "${YELLOW}Step 3: Running Selenium test...${NC}"
cd "$PROJECT_ROOT"

# Set environment variables if not already set
export WEBSITE_URL="${WEBSITE_URL:-https://localhost:3443}"
export TEST_USERNAME="${TEST_USERNAME:-admin@sentinelgrid.ai}"
export TEST_PASSWORD="${TEST_PASSWORD:-admin123}"
export HEADLESS="${HEADLESS:-false}"

echo "  Test configuration:"
echo "    WEBSITE_URL: $WEBSITE_URL"
echo "    TEST_USERNAME: $TEST_USERNAME"
echo "    HEADLESS: $HEADLESS"
echo ""

# Install test dependencies if needed
if [ ! -d "backend/tests" ]; then
    echo -e "${RED}❌ backend/tests directory not found!${NC}"
    exit 1
fi

# Check if pytest and selenium are installed
if ! python3 -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  pytest not found. Installing test dependencies...${NC}"
    pip install pytest selenium webdriver-manager
fi

# Run the specific test
echo "  Running test: test_welcome_dashboard_flow.py"
cd "$PROJECT_ROOT/backend"

pytest tests/test_welcome_dashboard_flow.py::TestWelcomeDashboardFlow::test_complete_flow_login_onboarding_dashboard \
    -v \
    --tb=short \
    --capture=no \
    -s

TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}=========================================="
    echo "✅ Test passed successfully!"
    echo "==========================================${NC}"
else
    echo -e "${RED}=========================================="
    echo "❌ Test failed!"
    echo "==========================================${NC}"
fi

exit $TEST_EXIT_CODE

