#!/bin/bash

# Run all detection system tests
# This script runs unit tests, integration tests, E2E tests, and Selenium UI tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}SentinelGrid Detection System Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Check environment
echo -e "${YELLOW}Checking environment...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠ Docker not found (optional for E2E tests)${NC}"
else
    echo -e "${GREEN}✓ Docker found${NC}"
fi

# Install test dependencies
echo
echo -e "${YELLOW}Installing test dependencies...${NC}"
pip install -q -r backend/tests/requirements-test.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create test screenshots directory
mkdir -p test_screenshots
echo -e "${GREEN}✓ Created test_screenshots directory${NC}"

# Run tests
echo
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Running Test Suites${NC}"
echo -e "${BLUE}========================================${NC}"

# 1. Unit Tests
echo
echo -e "${YELLOW}1. Unit Tests (Detection Models & Logic)${NC}"
cd backend/tests/siem
python -m pytest test_detection_monitors.py -v --tb=short || true
echo

# 2. E2E Integration Tests
echo -e "${YELLOW}2. End-to-End Integration Tests${NC}"
echo -e "${YELLOW}   (Requires: OpenSearch, PostgreSQL, SIEM Agent, SOAR Agent)${NC}"

# Check if services are running
if curl -s http://localhost:8001/health &> /dev/null && \
   curl -s http://localhost:8003/health &> /dev/null; then
    echo -e "${GREEN}✓ Services are running, executing E2E tests${NC}"
    python -m pytest test_e2e_detection_flow.py -v --tb=short || true
else
    echo -e "${YELLOW}⚠ Services not running, skipping E2E tests${NC}"
    echo -e "${YELLOW}  To run E2E tests:${NC}"
    echo -e "${YELLOW}    1. Start services: docker-compose up -d${NC}"
    echo -e "${YELLOW}    2. Run migrations${NC}"
    echo -e "${YELLOW}    3. Deploy monitors for test tenant${NC}"
    echo -e "${YELLOW}    4. Run this script again${NC}"
fi

echo

# 3. Selenium UI Tests
echo -e "${YELLOW}3. Selenium UI Tests (Frontend)${NC}"
echo -e "${YELLOW}   (Requires: Frontend running at http://localhost:3000)${NC}"

if curl -s http://localhost:3000 &> /dev/null; then
    echo -e "${GREEN}✓ Frontend is running, executing Selenium tests${NC}"
    python -m pytest test_detection_ui_selenium.py -v --tb=short || true
else
    echo -e "${YELLOW}⚠ Frontend not running, skipping Selenium tests${NC}"
    echo -e "${YELLOW}  To run UI tests:${NC}"
    echo -e "${YELLOW}    1. Start frontend: cd frontend && npm run dev${NC}"
    echo -e "${YELLOW}    2. Run this script again${NC}"
fi

echo

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"

if [ -d "test_screenshots" ] && [ "$(ls -A test_screenshots)" ]; then
    echo -e "${GREEN}✓ UI Screenshots available in: test_screenshots/${NC}"
    ls -1 test_screenshots/ | head -5
    echo
fi

echo -e "${GREEN}✓ Test execution complete${NC}"
echo
echo "Next steps:"
echo "  1. Review test results above"
echo "  2. Check test_screenshots/ for UI validation"
echo "  3. Review backend/tests/siem/*.py for test code"
echo
echo "To run specific test suites:"
echo "  Unit tests:     pytest backend/tests/siem/test_detection_monitors.py"
echo "  E2E tests:      pytest backend/tests/siem/test_e2e_detection_flow.py"
echo "  Selenium tests: pytest backend/tests/siem/test_detection_ui_selenium.py"
echo

