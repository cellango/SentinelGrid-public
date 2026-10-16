#!/bin/bash
# Run all onboarding-related tests

set -e

echo "=========================================="
echo "Running Onboarding Tests"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track test results
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run tests and track results
run_test_suite() {
    local service_name=$1
    local test_path=$2
    
    echo ""
    echo "${YELLOW}Testing: $service_name${NC}"
    echo "----------------------------------------"
    
    if pytest "$test_path" -v --tb=short; then
        echo "${GREEN}✅ $service_name tests passed${NC}"
        ((TESTS_PASSED++))
    else
        echo "${RED}❌ $service_name tests failed${NC}"
        ((TESTS_FAILED++))
    fi
}

# Backend tests
echo ""
echo "${YELLOW}=== Backend Tests ===${NC}"

# Tenant Service
run_test_suite "Tenant Service" "backend/services/tenant_service/tests/"

# Connector Service
run_test_suite "Connector Service" "backend/services/connector_service/tests/"

# Detection Service
run_test_suite "Detection Service" "backend/services/detection_service/tests/"

# Frontend tests
echo ""
echo "${YELLOW}=== Frontend Tests ===${NC}"
echo "----------------------------------------"

cd frontend

if npm test -- --passWithNoTests; then
    echo "${GREEN}✅ Frontend tests passed${NC}"
    ((TESTS_PASSED++))
else
    echo "${RED}❌ Frontend tests failed${NC}"
    ((TESTS_FAILED++))
fi

cd ..

# Summary
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "${GREEN}Passed: $TESTS_PASSED${NC}"
echo "${RED}Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo ""
    echo "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo ""
    echo "${RED}❌ Some tests failed${NC}"
    exit 1
fi

