#!/bin/bash
#
# Test Realm Architecture - Reset, Init, and Verify with Selenium
# 
# This script:
# 1. Resets Keycloak and database
# 2. Initializes realm architecture
# 3. Waits for services to be fully ready
# 4. Runs Selenium login test to verify dashboard access
#

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Configuration
DB_URL="${DB_URL:-postgresql://sg:sg@localhost:5432/sg}"
KEYCLOAK_URL="${KEYCLOAK_URL:-https://localhost:8443}"
WEBSITE_URL="${WEBSITE_URL:-https://localhost:3443}"
TEST_USERNAME="${TEST_USERNAME:-admin@sentinelgrid.ai}"
TEST_PASSWORD="${TEST_PASSWORD:-admin123}"

echo -e "${MAGENTA}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║                                                        ║${NC}"
echo -e "${MAGENTA}║     ${CYAN}Realm Architecture: Reset → Init → Test${MAGENTA}         ║${NC}"
echo -e "${MAGENTA}║                                                        ║${NC}"
echo -e "${MAGENTA}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Reset and initialize
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Step 1: Reset and Initialize Realm Architecture${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if [ -f "$SCRIPT_DIR/reset_and_init_realms.sh" ]; then
    bash "$SCRIPT_DIR/reset_and_init_realms.sh" -y
else
    echo -e "${RED}❌ Reset script not found: $SCRIPT_DIR/reset_and_init_realms.sh${NC}"
    exit 1
fi

echo ""

# Step 2: Additional wait for Keycloak stabilization
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Step 2: Waiting for Keycloak to Stabilize${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}Keycloak needs additional time to fully initialize after seeding...${NC}"
echo -e "${BLUE}Waiting 30 seconds for internal initialization...${NC}"

for i in {30..1}; do
    printf "\r${BLUE}   Time remaining: %2d seconds...${NC}" $i
    sleep 1
done
printf "\r${GREEN}✅ Keycloak stabilization period complete        ${NC}\n"

# Verify Keycloak realms are accessible
echo ""
echo -e "${YELLOW}Verifying Keycloak realms...${NC}"

REALMS=("sg-admin" "sg-mt-us-1" "sg-mt-eu-1")
for realm in "${REALMS[@]}"; do
    if curl -k -s "$KEYCLOAK_URL/realms/$realm" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Realm '$realm' is accessible${NC}"
    else
        echo -e "${RED}❌ Realm '$realm' not accessible${NC}"
        echo -e "${YELLOW}   Waiting 10 more seconds...${NC}"
        sleep 10
        if curl -k -s "$KEYCLOAK_URL/realms/$realm" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Realm '$realm' is now accessible${NC}"
        else
            echo -e "${RED}❌ Realm '$realm' still not accessible after wait${NC}"
            exit 1
        fi
    fi
done

echo ""

# Step 3: Verify platform admin user
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Step 3: Verify Platform Admin User${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}Testing token generation for admin@sentinelgrid.ai...${NC}"

# Try to get token
TOKEN_RESPONSE=$(curl -k -s -X POST "$KEYCLOAK_URL/realms/sg-admin/protocol/openid-connect/token" \
  -d "client_id=sg-admin-admin" \
  -d "username=$TEST_USERNAME" \
  -d "password=$TEST_PASSWORD" \
  -d "grant_type=password" \
  -d "scope=openid" || echo '{"error": "request_failed"}')

if echo "$TOKEN_RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✅ Successfully obtained token for $TEST_USERNAME${NC}"
    
    # Extract and decode token to verify claims
    ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    
    # Decode token payload (middle part)
    TOKEN_PAYLOAD=$(echo "$ACCESS_TOKEN" | cut -d. -f2)
    # Add padding if needed for base64
    case $((${#TOKEN_PAYLOAD} % 4)) in
        2) TOKEN_PAYLOAD="${TOKEN_PAYLOAD}==" ;;
        3) TOKEN_PAYLOAD="${TOKEN_PAYLOAD}=" ;;
    esac
    
    DECODED=$(echo "$TOKEN_PAYLOAD" | base64 -d 2>/dev/null || echo '{}')
    
    # Check for expected claims
    if echo "$DECODED" | grep -q "PLATFORM_ADMIN"; then
        echo -e "${GREEN}✅ Token contains PLATFORM_ADMIN role${NC}"
    else
        echo -e "${YELLOW}⚠️  PLATFORM_ADMIN role not found in token${NC}"
    fi
    
else
    echo -e "${RED}❌ Failed to obtain token for $TEST_USERNAME${NC}"
    echo -e "${YELLOW}   Response: $TOKEN_RESPONSE${NC}"
    echo ""
    echo -e "${YELLOW}This might mean:${NC}"
    echo -e "  1. User was not created during seeding"
    echo -e "  2. Password is incorrect"
    echo -e "  3. Keycloak is not fully ready yet"
    echo ""
    echo -e "${BLUE}Continuing to Selenium test anyway (it will fail if auth doesn't work)...${NC}"
fi

echo ""

# Step 4: Check if frontend is running
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Step 4: Verify Frontend Service${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}Checking if frontend is running...${NC}"

if curl -k -s "$WEBSITE_URL" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend is accessible at $WEBSITE_URL${NC}"
else
    echo -e "${RED}❌ Frontend not accessible at $WEBSITE_URL${NC}"
    echo -e "${YELLOW}   Make sure frontend service is running:${NC}"
    echo -e "${BLUE}   docker-compose up -d frontend${NC}"
    echo ""
    echo -e "${YELLOW}Continuing anyway (test will fail if frontend is not ready)...${NC}"
fi

echo ""

# Step 5: Run Selenium test
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Step 5: Run Selenium Login Test${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}Running Selenium test: TestSimpleLogin::test_simple_login_to_dashboard${NC}"
echo ""
echo -e "${BLUE}Test Configuration:${NC}"
echo -e "  • Website URL: $WEBSITE_URL"
echo -e "  • Test User: $TEST_USERNAME"
echo -e "  • Test Password: $TEST_PASSWORD"
echo -e "  • Headless Mode: ${HEADLESS:-false}"
echo ""

cd "$PROJECT_ROOT"

# Set environment variables for test
export WEBSITE_URL="$WEBSITE_URL"
export TEST_USERNAME="$TEST_USERNAME"
export TEST_PASSWORD="$TEST_PASSWORD"
export DB_URL="$DB_URL"
export IAM_AGENT_URL="${IAM_AGENT_URL:-http://localhost:8005}"

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest not found${NC}"
    echo -e "${YELLOW}   Install with: pip install pytest selenium${NC}"
    exit 1
fi

# Check if selenium is installed
if ! python3 -c "import selenium" 2>/dev/null; then
    echo -e "${RED}❌ selenium package not found${NC}"
    echo -e "${YELLOW}   Install with: pip install selenium${NC}"
    exit 1
fi

# Run the test
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if pytest backend/tests/test_auth_selenium.py::TestSimpleLogin::test_simple_login_to_dashboard -v -s; then
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                        ║${NC}"
    echo -e "${GREEN}║              ${CYAN}✅ ALL TESTS PASSED!${GREEN}                     ║${NC}"
    echo -e "${GREEN}║                                                        ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}Test Results${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${GREEN}✅${NC} Keycloak database reset and initialized"
    echo -e "  ${GREEN}✅${NC} Realms created (sg-admin, sg-mt-us-1, sg-mt-eu-1)"
    echo -e "  ${GREEN}✅${NC} Platform admin user created (admin@sentinelgrid.ai)"
    echo -e "  ${GREEN}✅${NC} Login successful"
    echo -e "  ${GREEN}✅${NC} Dashboard accessible"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${GREEN}Realm architecture is working correctly! 🎉${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                                                        ║${NC}"
    echo -e "${RED}║              ${YELLOW}❌ TEST FAILED${RED}                            ║${NC}"
    echo -e "${RED}║                                                        ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Troubleshooting steps:${NC}"
    echo ""
    echo -e "  ${BLUE}1. Check Keycloak logs:${NC}"
    echo -e "     ${CYAN}docker-compose logs keycloak | tail -50${NC}"
    echo ""
    echo -e "  ${BLUE}2. Check frontend logs:${NC}"
    echo -e "     ${CYAN}docker-compose logs frontend | tail -50${NC}"
    echo ""
    echo -e "  ${BLUE}3. Verify user exists in Keycloak:${NC}"
    echo -e "     ${CYAN}curl -k $KEYCLOAK_URL/admin/realms/sg-admin/users -u admin:admin${NC}"
    echo ""
    echo -e "  ${BLUE}4. Test token generation manually:${NC}"
    echo -e "     ${CYAN}curl -k -X POST $KEYCLOAK_URL/realms/sg-admin/protocol/openid-connect/token \\${NC}"
    echo -e "       ${CYAN}-d \"client_id=sg-admin-admin\" \\${NC}"
    echo -e "       ${CYAN}-d \"username=$TEST_USERNAME\" \\${NC}"
    echo -e "       ${CYAN}-d \"password=$TEST_PASSWORD\" \\${NC}"
    echo -e "       ${CYAN}-d \"grant_type=password\"${NC}"
    echo ""
    echo -e "  ${BLUE}5. Check database:${NC}"
    echo -e "     ${CYAN}psql $DB_URL -c \"SELECT * FROM realms;\"${NC}"
    echo ""
    exit 1
fi

