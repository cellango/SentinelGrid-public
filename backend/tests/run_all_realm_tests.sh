#!/bin/bash
# Comprehensive test runner for all realm strategy tests
# Automatically handles conda environment activation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Realm Strategy Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo -e "${RED}Error: conda is not installed or not in PATH${NC}"
    exit 1
fi

# Determine conda environment name
ENV_NAME="${CONDA_ENV_NAME:-SentinelTest}"

# Check if SentinelTest exists, if not try 'test'
if ! conda env list | grep -q "^${ENV_NAME} "; then
    if conda env list | grep -q "^test "; then
        ENV_NAME="test"
        echo -e "${YELLOW}Using 'test' environment instead of 'SentinelTest'${NC}"
    fi
fi

echo -e "${BLUE}Using conda environment: ${ENV_NAME}${NC}"
echo ""

# Fix pydantic version if needed
echo -e "${YELLOW}Checking dependencies...${NC}"
conda run -n "$ENV_NAME" pip install --upgrade pydantic-core --quiet 2>/dev/null || true

# Test files
UNIT_TESTS="test_auth_api_client.py::TestPricingService test_auth_api_client.py::TestRealmManager"
INTEGRATION_TESTS="test_realm_strategy_integration.py"

# Build pytest command
PYTEST_CMD="conda run -n $ENV_NAME python -m pytest -v --tb=short"

# Parse arguments
RUN_COVERAGE=false
if [ "$1" == "--coverage" ]; then
    RUN_COVERAGE=true
    PYTEST_CMD="$PYTEST_CMD --cov=app.services.pricing_service --cov=app.services.realm_manager --cov-report=term-missing --cov-report=html"
    echo -e "${BLUE}Coverage reporting enabled${NC}"
fi

# Add test files
PYTEST_CMD="$PYTEST_CMD $UNIT_TESTS $INTEGRATION_TESTS"

echo -e "${BLUE}Running all realm strategy tests...${NC}"
echo -e "${BLUE}Command: $PYTEST_CMD${NC}"
echo ""

# Run tests
START_TIME=$(date +%s)

if eval "$PYTEST_CMD"; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo -e "${GREEN}Duration: ${DURATION}s${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    if [ "$RUN_COVERAGE" = true ]; then
        echo ""
        echo -e "${BLUE}Coverage report generated in htmlcov/index.html${NC}"
    fi
    
    exit 0
else
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ Some tests failed${NC}"
    echo -e "${RED}Duration: ${DURATION}s${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi

