#!/bin/bash
# Test runner for Realm Strategy tests
# Runs all realm strategy related tests with proper conda environment

set -e  # Exit on error

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
echo -e "${BLUE}Realm Strategy Test Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo -e "${RED}Error: conda is not installed or not in PATH${NC}"
    echo "Please install conda: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Determine conda environment name (default to SentinelTest, can override with CONDA_ENV_NAME)
# Also check for 'test' environment as fallback
ENV_NAME="${CONDA_ENV_NAME:-SentinelTest}"

# Check if SentinelTest exists, if not try 'test'
if ! conda env list | grep -q "^${ENV_NAME} "; then
    if conda env list | grep -q "^test "; then
        ENV_NAME="test"
        echo -e "${YELLOW}Using 'test' environment instead of 'SentinelTest'${NC}"
    fi
fi

echo -e "${YELLOW}Checking conda environment: ${ENV_NAME}${NC}"

# Check if environment exists
if ! conda env list | grep -q "^${ENV_NAME} "; then
    echo -e "${YELLOW}Environment ${ENV_NAME} not found. Creating from environment.yml...${NC}"
    if [ -f "environment.yml" ]; then
        conda env create -f environment.yml
    else
        echo -e "${RED}Error: environment.yml not found${NC}"
        exit 1
    fi
fi

# Activate conda environment
echo -e "${GREEN}Activating conda environment: ${ENV_NAME}${NC}"
eval "$(conda shell.bash hook)"
conda activate "${ENV_NAME}"

# Verify activation
if [ "$CONDA_DEFAULT_ENV" != "${ENV_NAME}" ]; then
    echo -e "${RED}Error: Failed to activate conda environment ${ENV_NAME}${NC}"
    exit 1
fi

echo -e "${GREEN}Conda environment activated: ${CONDA_DEFAULT_ENV}${NC}"
echo ""

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed in ${ENV_NAME}${NC}"
    echo "Installing pytest..."
    pip install pytest pytest-asyncio pytest-cov
fi

# Fix pydantic version conflict if needed
echo -e "${YELLOW}Checking pydantic version compatibility...${NC}"
PYDANTIC_VERSION=$(python -c "import pydantic; print(pydantic.__version__)" 2>/dev/null || echo "")
if [ -n "$PYDANTIC_VERSION" ]; then
    # Check if pydantic-core version matches
    PYDANTIC_CORE_VERSION=$(python -c "import pydantic_core; print(pydantic_core.__version__)" 2>/dev/null || echo "")
    if [ -n "$PYDANTIC_CORE_VERSION" ]; then
        echo -e "${BLUE}Pydantic: $PYDANTIC_VERSION, Pydantic-core: $PYDANTIC_CORE_VERSION${NC}"
        # Try to fix if there's a mismatch
        python -c "import pydantic" 2>&1 | grep -q "incompatible" && {
            echo -e "${YELLOW}Fixing pydantic version conflict...${NC}"
            pip install --upgrade pydantic-core 2>/dev/null || true
        }
    fi
fi

# Test files to run
UNIT_TEST_FILE="test_auth_api_client.py"
INTEGRATION_TEST_FILE="test_realm_strategy_integration.py"

# Check if test files exist
if [ ! -f "$UNIT_TEST_FILE" ]; then
    echo -e "${RED}Error: $UNIT_TEST_FILE not found${NC}"
    exit 1
fi

if [ ! -f "$INTEGRATION_TEST_FILE" ]; then
    echo -e "${RED}Error: $INTEGRATION_TEST_FILE not found${NC}"
    exit 1
fi

# Parse command line arguments
RUN_UNIT=true
RUN_INTEGRATION=true
RUN_COVERAGE=false
VERBOSE=false
MARKERS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit-only)
            RUN_UNIT=true
            RUN_INTEGRATION=false
            shift
            ;;
        --integration-only)
            RUN_UNIT=false
            RUN_INTEGRATION=true
            shift
            ;;
        --coverage)
            RUN_COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -m|--marker)
            MARKERS="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --unit-only          Run only unit tests"
            echo "  --integration-only  Run only integration tests"
            echo "  --coverage          Generate coverage report"
            echo "  -v, --verbose       Verbose output"
            echo "  -m, --marker MARKER Run tests with specific marker"
            echo "  --help              Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Run all tests"
            echo "  $0 --unit-only                       # Run only unit tests"
            echo "  $0 --coverage                        # Run with coverage"
            echo "  $0 -m integration                    # Run only integration tests"
            echo "  $0 -k compliance                    # Run tests matching 'compliance'"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest"

# Always add verbosity for better output
PYTEST_CMD="$PYTEST_CMD -v"

# Add markers
if [ -n "$MARKERS" ]; then
    PYTEST_CMD="$PYTEST_CMD -m $MARKERS"
fi

# Add coverage if requested
if [ "$RUN_COVERAGE" = true ]; then
    # Install coverage tools if needed
    if ! python -c "import pytest_cov" 2>/dev/null; then
        echo -e "${YELLOW}Installing pytest-cov for coverage...${NC}"
        pip install pytest-cov
    fi
    PYTEST_CMD="$PYTEST_CMD --cov=app.services.pricing_service --cov=app.services.realm_manager --cov-report=term-missing --cov-report=html"
    echo -e "${BLUE}Coverage reporting enabled${NC}"
fi

# Build test file list
TEST_FILES=""
if [ "$RUN_UNIT" = true ]; then
    TEST_FILES="$UNIT_TEST_FILE"
fi

if [ "$RUN_INTEGRATION" = true ]; then
    if [ -n "$TEST_FILES" ]; then
        TEST_FILES="$TEST_FILES $INTEGRATION_TEST_FILE"
    else
        TEST_FILES="$INTEGRATION_TEST_FILE"
    fi
fi

# Add test files to command
PYTEST_CMD="$PYTEST_CMD $TEST_FILES"

echo -e "${BLUE}Running tests...${NC}"
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

