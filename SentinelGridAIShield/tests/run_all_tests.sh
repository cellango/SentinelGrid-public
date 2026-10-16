#!/bin/bash
# Run all SentinelGridAIShield tests

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

echo "🧪 Running SentinelGridAIShield Test Suite"
echo "==========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Track results
GATEWAY_TESTS=0
SERVICES_TESTS=0
INTEGRATION_TESTS=0
E2E_TESTS=0

# Test 1: Gateway unit tests
echo -e "${BLUE}[1/4] Gateway Unit Tests${NC}"
echo "-------------------------"
cd "$REPO_ROOT/gateway"
if go test -v ./... ; then
    echo -e "${GREEN}✓ Gateway tests passed${NC}"
    GATEWAY_TESTS=1
else
    echo -e "${RED}✗ Gateway tests failed${NC}"
fi
cd "$REPO_ROOT"
echo ""

# Test 2: Services unit tests
echo -e "${BLUE}[2/4] Services Unit Tests${NC}"
echo "-------------------------"
cd "$REPO_ROOT/services"
if pytest -v; then
    echo -e "${GREEN}✓ Services tests passed${NC}"
    SERVICES_TESTS=1
else
    echo -e "${RED}✗ Services tests failed${NC}"
fi
cd "$REPO_ROOT"
echo ""

# Test 3: Integration tests
echo -e "${BLUE}[3/4] Integration Tests${NC}"
echo "-----------------------"
if "$SCRIPT_DIR/integration_test.sh"; then
    echo -e "${GREEN}✓ Integration tests passed${NC}"
    INTEGRATION_TESTS=1
else
    echo -e "${RED}✗ Integration tests failed${NC}"
fi
echo ""

# Test 4: E2E tests
echo -e "${BLUE}[4/4] End-to-End Tests${NC}"
echo "----------------------"
if python3 "$SCRIPT_DIR/e2e_test.py"; then
    echo -e "${GREEN}✓ E2E tests passed${NC}"
    E2E_TESTS=1
else
    echo -e "${RED}✗ E2E tests failed${NC}"
fi
echo ""

# Summary
echo "==========================================="
echo "Test Summary"
echo "==========================================="
TOTAL=$((GATEWAY_TESTS + SERVICES_TESTS + INTEGRATION_TESTS + E2E_TESTS))

if [ $GATEWAY_TESTS -eq 1 ]; then GATEWAY_STATUS="${GREEN}PASS${NC}"; else GATEWAY_STATUS="${RED}FAIL${NC}"; fi
if [ $SERVICES_TESTS -eq 1 ]; then SERVICES_STATUS="${GREEN}PASS${NC}"; else SERVICES_STATUS="${RED}FAIL${NC}"; fi
if [ $INTEGRATION_TESTS -eq 1 ]; then INTEGRATION_STATUS="${GREEN}PASS${NC}"; else INTEGRATION_STATUS="${RED}FAIL${NC}"; fi
if [ $E2E_TESTS -eq 1 ]; then E2E_STATUS="${GREEN}PASS${NC}"; else E2E_STATUS="${RED}FAIL${NC}"; fi

echo -e "Gateway Tests:      ${GATEWAY_STATUS}"
echo -e "Services Tests:     ${SERVICES_STATUS}"
echo -e "Integration Tests:  ${INTEGRATION_STATUS}"
echo -e "E2E Tests:          ${E2E_STATUS}"
echo ""
echo "Total: $TOTAL/4 test suites passed"

if [ $TOTAL -eq 4 ]; then
    echo ""
    echo -e "${GREEN}🎉 ALL TEST SUITES PASSED!${NC}"
    echo "System is ready for production deployment"
    exit 0
else
    echo ""
    echo -e "${RED}⚠️  SOME TESTS FAILED${NC}"
    echo "Review failures and fix before deploying"
    exit 1
fi
