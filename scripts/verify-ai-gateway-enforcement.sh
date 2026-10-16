#!/bin/bash
#
# Verify AI Gateway Enforcement
# ==============================
#
# Tests that network policies correctly block direct AI provider access
# and allow traffic through SentinelGrid AI Shield gateway
#
# Usage:
#   ./verify-ai-gateway-enforcement.sh [gateway-url]
#
# Example:
#   ./verify-ai-gateway-enforcement.sh http://localhost:8023
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
GATEWAY_URL="${1:-http://localhost:8023}"
TIMEOUT=5

echo "========================================="
echo "SentinelGrid AI Gateway Enforcement Test"
echo "========================================="
echo ""
echo "Gateway URL: $GATEWAY_URL"
echo "Timeout: ${TIMEOUT}s"
echo ""

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
test_connection() {
    local name="$1"
    local url="$2"
    local expect_success="$3"  # "true" or "false"
    
    echo -n "Testing $name... "
    
    if curl -s -m "$TIMEOUT" -o /dev/null -w "%{http_code}" "$url" > /dev/null 2>&1; then
        response_code=$?
        if [ "$expect_success" = "true" ]; then
            echo -e "${GREEN}✓ PASS${NC} (accessible as expected)"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo -e "${RED}✗ FAIL${NC} (should be blocked but is accessible)"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    else
        if [ "$expect_success" = "false" ]; then
            echo -e "${GREEN}✓ PASS${NC} (blocked as expected)"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo -e "${RED}✗ FAIL${NC} (should be accessible but is blocked)"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    fi
}

echo "1. Testing AI Provider Blocking"
echo "--------------------------------"

# These should FAIL (be blocked)
test_connection "OpenAI Direct Access" "https://api.openai.com/v1/models" "false"
test_connection "Anthropic Direct Access" "https://api.anthropic.com/v1/messages" "false"
test_connection "Cohere Direct Access" "https://api.cohere.ai/v1/models" "false"

echo ""
echo "2. Testing Gateway Access"
echo "-------------------------"

# Gateway should be accessible
test_connection "Gateway Health Check" "${GATEWAY_URL}/health" "true"
test_connection "Gateway v1 Endpoint" "${GATEWAY_URL}/v1/chat/completions" "true"

echo ""
echo "3. DNS Resolution Test"
echo "----------------------"

# DNS should work (we block at network layer, not DNS layer)
echo -n "Testing DNS resolution for api.openai.com... "
if nslookup api.openai.com > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC} (DNS works - good)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${YELLOW}⚠ WARN${NC} (DNS blocked - may be overly restrictive)"
fi

echo ""
echo "4. Testing Internal Connectivity"
echo "---------------------------------"

# Internal services should be accessible (adjust as needed)
echo -n "Testing localhost connectivity... "
if curl -s -m "$TIMEOUT" http://localhost > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC} (localhost accessible)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${YELLOW}⚠ WARN${NC} (localhost not accessible)"
fi

echo ""
echo "5. Enforcement Summary"
echo "----------------------"
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Your network policies are correctly enforcing AI gateway usage."
    echo "Direct access to AI providers is blocked."
    echo ""
    echo "Next steps:"
    echo "1. Deploy SentinelGrid Endpoint Protection agent for detection"
    echo "2. Monitor compliance dashboard for any bypass attempts"
    echo "3. Review usage reconciliation reports weekly"
    exit 0
else
    echo -e "${RED}✗ Some tests failed!${NC}"
    echo ""
    echo "Network policies may not be correctly configured."
    echo ""
    echo "Troubleshooting:"
    echo "1. AWS: Check security group rules - sg-*****"
    echo "2. Kubernetes: kubectl get networkpolicies -A"
    echo "3. Azure: Check NSG rules in Azure Portal"
    echo "4. Check firewall logs for blocked connections"
    echo "5. Verify gateway endpoint is correct: $GATEWAY_URL"
    exit 1
fi

