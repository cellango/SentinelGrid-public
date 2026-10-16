#!/bin/bash
# Script to run authentication tests with proper conda environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo -e "${RED}Error: conda is not installed or not in PATH${NC}"
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Determine conda environment name (default to SentinelTest, can override with CONDA_ENV_NAME)
ENV_NAME="${CONDA_ENV_NAME:-SentinelTest}"

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

# Install/update test dependencies if needed
if [ "$1" == "--install-deps" ]; then
    echo -e "${YELLOW}Installing test dependencies...${NC}"
    pip install -r requirements.txt
fi

# Run tests based on arguments
if [ -z "$1" ] || [ "$1" == "--install-deps" ]; then
    # Run all auth tests
    echo -e "${GREEN}Running all authentication tests...${NC}"
    pytest test_auth_*.py -v
elif [ "$1" == "unit" ]; then
    echo -e "${GREEN}Running unit tests...${NC}"
    pytest test_auth_api_client.py -v -m unit
elif [ "$1" == "integration" ]; then
    echo -e "${GREEN}Running integration tests...${NC}"
    pytest test_auth_endpoints.py -v -m integration
elif [ "$1" == "selenium" ]; then
    echo -e "${GREEN}Running Selenium E2E tests...${NC}"
    CI="${CI:-false}" pytest test_auth_selenium.py -v -m selenium
elif [ "$1" == "coverage" ]; then
    echo -e "${GREEN}Running tests with coverage...${NC}"
    pytest test_auth_*.py --cov=backend.services.iam_agent --cov-report=html --cov-report=term-missing
else
    echo -e "${YELLOW}Usage: $0 [unit|integration|selenium|coverage|--install-deps]${NC}"
    echo -e "${YELLOW}  unit          - Run unit tests only${NC}"
    echo -e "${YELLOW}  integration   - Run integration tests only${NC}"
    echo -e "${YELLOW}  selenium      - Run Selenium E2E tests only${NC}"
    echo -e "${YELLOW}  coverage      - Run all tests with coverage report${NC}"
    echo -e "${YELLOW}  --install-deps - Install test dependencies${NC}"
    exit 1
fi

echo -e "${GREEN}Tests completed!${NC}"

