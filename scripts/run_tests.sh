#!/bin/bash
# Test runner script for SentinelGrid
# Usage: ./scripts/run_tests.sh [service] [options]
# Uses conda environment: test (or SentinelTest if test doesn't exist)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Conda environment name (prefer 'test', fallback to 'SentinelTest')
CONDA_ENV=""
if command -v conda &> /dev/null; then
    eval "$(conda shell.bash hook)"
    if conda env list 2>/dev/null | grep -qE "^\s*test\s"; then
        CONDA_ENV="test"
    elif conda env list 2>/dev/null | grep -qE "^\s*SentinelTest\s"; then
        CONDA_ENV="SentinelTest"
    else
        CONDA_ENV="test"  # Default, will create if needed
    fi
fi

# Default options
SERVICE=""
COVERAGE=false
VERBOSE=false
MARKERS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --service|-s)
            SERVICE="$2"
            shift 2
            ;;
        --coverage|-c)
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --marker|-m)
            MARKERS="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -s, --service SERVICE    Run tests for specific service (iam_agent, api_gateway, model_gateway)"
            echo "  -c, --coverage          Run with coverage report"
            echo "  -v, --verbose           Verbose output"
            echo "  -m, --marker MARKER     Run tests with specific marker (unit, integration, e2e)"
            echo "  -h, --help              Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Set PYTHONPATH to include canonical service directories for imports
export PYTHONPATH="$PROJECT_ROOT/backend/agents/iam_agent:$PROJECT_ROOT/backend/services/api_gateway:$PROJECT_ROOT/backend/services/model_gateway:$PROJECT_ROOT/backend/libs:$PYTHONPATH"

echo -e "${GREEN}🧪 SentinelGrid Test Runner${NC}"
echo ""

# Check if conda is available and set up environment
USE_CONDA=false
CONDA_PREFIX=""
if command -v conda &> /dev/null; then
    USE_CONDA=true
    echo -e "${GREEN}✅ Conda found${NC}"
    
    # Initialize conda for bash (needed for conda env list)
    eval "$(conda shell.bash hook)" 2>/dev/null || true
    
    # Check if conda environment exists
    if conda env list 2>/dev/null | grep -qE "^\s*${CONDA_ENV}\s"; then
        echo -e "${GREEN}✅ Conda environment '$CONDA_ENV' found${NC}"
        
        # Get conda environment path
        CONDA_PREFIX=$(conda env list 2>/dev/null | grep -E "^\s*${CONDA_ENV}\s" | awk '{print $NF}')
        if [ -n "$CONDA_PREFIX" ] && [ -d "$CONDA_PREFIX" ]; then
            echo -e "${YELLOW}Using conda environment: $CONDA_ENV${NC}"
            echo -e "${GREEN}   Path: $CONDA_PREFIX${NC}"
            # Set PATH to use conda environment's Python
            export PATH="$CONDA_PREFIX/bin:$PATH"
            echo -e "${GREEN}✅ Python: $(python --version 2>&1)${NC}"
        else
            echo -e "${YELLOW}⚠️  Could not locate conda environment path, using system Python${NC}"
            USE_CONDA=false
        fi
    else
        echo -e "${YELLOW}⚠️  Conda environment '$CONDA_ENV' not found${NC}"
        echo -e "${YELLOW}Creating environment from backend/tests/environment.yml...${NC}"
        if [ -f "backend/tests/environment.yml" ]; then
            conda env create -f backend/tests/environment.yml 2>&1 | grep -v "^$" || {
                echo -e "${RED}❌ Failed to create conda environment${NC}"
                echo "Falling back to system Python"
                USE_CONDA=false
            }
            if [ "$USE_CONDA" = true ]; then
                CONDA_PREFIX=$(conda env list 2>/dev/null | grep -E "^\s*${CONDA_ENV}\s" | awk '{print $NF}')
                if [ -n "$CONDA_PREFIX" ] && [ -d "$CONDA_PREFIX" ]; then
                    export PATH="$CONDA_PREFIX/bin:$PATH"
                    echo -e "${GREEN}✅ Environment created${NC}"
                fi
            fi
        else
            echo -e "${RED}❌ environment.yml not found${NC}"
            echo "Falling back to system Python"
            USE_CONDA=false
        fi
    fi
else
    echo -e "${YELLOW}⚠️  Conda not found, using system Python${NC}"
fi

echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest is not installed${NC}"
    if [ "$USE_CONDA" = true ] && [ -n "$CONDA_PREFIX" ]; then
        echo "Installing test dependencies in conda environment..."
        "$CONDA_PREFIX/bin/pip" install pytest pytest-asyncio pytest-cov httpx fastapi[test] || {
            echo -e "${YELLOW}⚠️  Failed to install via conda pip, trying system pip${NC}"
            pip install pytest pytest-asyncio pytest-cov httpx fastapi[test] || {
                echo -e "${RED}❌ Failed to install pytest${NC}"
                exit 1
            }
        }
    else
        echo "Installing test dependencies..."
        pip install pytest pytest-asyncio pytest-cov httpx fastapi[test] || {
            echo -e "${RED}❌ Failed to install pytest${NC}"
            exit 1
        }
    fi
fi

# Build pytest command
PYTEST_CMD="pytest"
TEST_PATHS=()

if [ -n "$SERVICE" ]; then
    # Run tests for specific service
    SERVICE_PATH="backend/services/$SERVICE/tests"
    if [ ! -d "$SERVICE_PATH" ]; then
        echo -e "${RED}❌ Service '$SERVICE' not found or has no tests${NC}"
        exit 1
    fi
    TEST_PATHS=("$SERVICE_PATH")
    echo -e "${YELLOW}📦 Running tests for: $SERVICE${NC}"
else
    # Run all tests
    TEST_PATHS=(
        "backend/agents/iam_agent/tests"
        "backend/services/api_gateway/tests"
        "backend/services/model_gateway/tests"
    )
    echo -e "${YELLOW}📦 Running all tests${NC}"
fi

# Add markers if specified
if [ -n "$MARKERS" ]; then
    PYTEST_CMD="$PYTEST_CMD -m $MARKERS"
fi

# Add verbose flag
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
else
    PYTEST_CMD="$PYTEST_CMD -v"
fi

# Add coverage if requested
if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=backend --cov-report=html --cov-report=term --cov-report=term-missing"
    echo -e "${YELLOW}📊 Coverage report will be generated${NC}"
fi

# Add test paths
for path in "${TEST_PATHS[@]}"; do
    if [ -d "$path" ]; then
        PYTEST_CMD="$PYTEST_CMD $path"
    fi
done

echo ""
echo -e "${GREEN}Running: $PYTEST_CMD${NC}"
echo ""

# Execute tests
eval $PYTEST_CMD

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    if [ "$COVERAGE" = true ]; then
        echo -e "${GREEN}📊 Coverage report: htmlcov/index.html${NC}"
    fi
else
    echo -e "${RED}❌ Some tests failed (exit code: $EXIT_CODE)${NC}"
fi

exit $EXIT_CODE
