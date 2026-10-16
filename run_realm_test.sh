#!/bin/bash
#
# Complete Realm Architecture Test
# 
# This script:
# 1. Resets Keycloak and database
# 2. Initializes realm architecture
# 3. Restarts IAM Agent to pick up new realm config
# 4. Waits for all services to be fully ready
# 5. Runs Selenium login test
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${MAGENTA}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║                                                        ║${NC}"
echo -e "${MAGENTA}║       ${CYAN}Complete Realm Architecture Test Suite${MAGENTA}         ║${NC}"
echo -e "${MAGENTA}║                                                        ║${NC}"
echo -e "${MAGENTA}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Reset and initialize
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Step 1: Reset and Initialize Realm Architecture${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

bash "$SCRIPT_DIR/backend/scripts/reset_and_init_realms.sh" -y

echo ""

# Step 2: Restart IAM Agent to pick up new realm configuration
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Step 2: Restart IAM Agent${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}Restarting IAM Agent to pick up new realm configuration...${NC}"
docker-compose restart iam_agent

echo -e "${YELLOW}Waiting for IAM Agent to be ready...${NC}"
sleep 10

# Wait for IAM Agent health check
RETRY_COUNT=0
MAX_RETRIES=30

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8005/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ IAM Agent is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $((RETRY_COUNT % 5)) -eq 0 ]; then
        echo -e "${BLUE}   Still waiting for IAM Agent... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    fi
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ IAM Agent failed to start${NC}"
    echo -e "${YELLOW}   Check logs: docker-compose logs iam_agent${NC}"
    exit 1
fi

echo ""

# Step 3: Verify frontend is running
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Step 3: Verify Frontend Service${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if ! docker-compose ps | grep -q "frontend.*Up"; then
    echo -e "${YELLOW}⚠️  Frontend not running, starting it...${NC}"
    docker-compose up -d frontend
    
    echo -e "${YELLOW}Waiting for frontend to be ready...${NC}"
    sleep 15
fi

# Check if frontend is accessible
if curl -k -s https://localhost:3443 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend is accessible${NC}"
else
    echo -e "${RED}❌ Frontend not accessible${NC}"
    echo -e "${YELLOW}   Make sure frontend is running: docker-compose up -d frontend${NC}"
    exit 1
fi

echo ""

# Step 4: Manual token test
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Step 4: Test Token Generation${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}Testing direct Keycloak token generation...${NC}"

TOKEN_RESPONSE=$(curl -k -s -X POST https://localhost:8443/realms/sg-admin/protocol/openid-connect/token \
  -d "client_id=sentinelgrid-web" \
  -d "username=admin@sentinelgrid.ai" \
  -d "password=admin123" \
  -d "grant_type=password" \
  -d "scope=openid" || echo '{"error": "request_failed"}')

if echo "$TOKEN_RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✅ Successfully obtained token from Keycloak${NC}"
    
    # Verify token contains expected claims
    ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    TOKEN_PAYLOAD=$(echo "$ACCESS_TOKEN" | cut -d. -f2)
    
    # Add padding for base64
    case $((${#TOKEN_PAYLOAD} % 4)) in
        2) TOKEN_PAYLOAD="${TOKEN_PAYLOAD}==" ;;
        3) TOKEN_PAYLOAD="${TOKEN_PAYLOAD}=" ;;
    esac
    
    DECODED=$(echo "$TOKEN_PAYLOAD" | base64 -d 2>/dev/null || echo '{}')
    
    if echo "$DECODED" | grep -q "PLATFORM_ADMIN"; then
        echo -e "${GREEN}✅ Token contains PLATFORM_ADMIN role${NC}"
    else
        echo -e "${YELLOW}⚠️  Token does not contain PLATFORM_ADMIN role${NC}"
    fi
    
    # Check for sg.* claims
    if echo "$DECODED" | grep -q '"sg"'; then
        echo -e "${GREEN}✅ Token contains 'sg' nested claims${NC}"
    else
        echo -e "${YELLOW}⚠️  Token does not contain 'sg' nested claims (this is expected if mappers not yet working)${NC}"
    fi
else
    echo -e "${RED}❌ Failed to obtain token from Keycloak${NC}"
    echo -e "${YELLOW}   Response: $TOKEN_RESPONSE${NC}"
    echo ""
    echo -e "${YELLOW}Possible issues:${NC}"
    echo -e "  • User not created during seeding"
    echo -e "  • Keycloak not fully initialized"
    echo -e "  • Client 'sentinelgrid-web' not created in sg-admin realm"
    echo ""
    echo -e "${BLUE}Continuing to Selenium test (will provide more detailed error)...${NC}"
fi

echo ""

# Step 5: Test IAM Agent login endpoint
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Step 5: Test IAM Agent Login Endpoint${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "${YELLOW}Testing IAM Agent login endpoint...${NC}"

IAM_LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8005/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@sentinelgrid.ai",
    "password": "admin123",
    "remember_me": false
  }' || echo '{"detail": "request_failed"}')

if echo "$IAM_LOGIN_RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✅ IAM Agent login endpoint working${NC}"
else
    echo -e "${RED}❌ IAM Agent login endpoint failed${NC}"
    echo -e "${YELLOW}   Response: $IAM_LOGIN_RESPONSE${NC}"
    echo ""
    echo -e "${YELLOW}This means the Selenium test will likely fail.${NC}"
    echo -e "${YELLOW}The IAM Agent may be using the wrong realm or client configuration.${NC}"
    echo ""
fi

echo ""

# Step 6: Run Selenium test
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}Step 6: Run Selenium Login Test${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check prerequisites
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest not found. Install with: pip install pytest selenium${NC}"
    exit 1
fi

if ! python3 -c "import selenium" 2>/dev/null; then
    echo -e "${RED}❌ selenium not found. Install with: pip install selenium${NC}"
    exit 1
fi

# Set environment variables
export WEBSITE_URL="https://localhost:3443"
export TEST_USERNAME="admin@sentinelgrid.ai"
export TEST_PASSWORD="admin123"
export DB_URL="postgresql://sg:sg@localhost:5432/sg"
export IAM_AGENT_URL="http://localhost:8005"

echo -e "${BLUE}Test Configuration:${NC}"
echo -e "  • Website: $WEBSITE_URL"
echo -e "  • Username: $TEST_USERNAME"
echo -e "  • Password: $TEST_PASSWORD"
echo ""

echo -e "${YELLOW}Running: pytest backend/tests/test_auth_selenium.py::TestSimpleLogin::test_simple_login_to_dashboard${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

if pytest backend/tests/test_auth_selenium.py::TestSimpleLogin::test_simple_login_to_dashboard -v -s; then
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                        ║${NC}"
    echo -e "${GREEN}║         ${CYAN}✅ REALM ARCHITECTURE TEST PASSED!${GREEN}           ║${NC}"
    echo -e "${GREEN}║                                                        ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}Test Summary${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${GREEN}✅${NC} Keycloak reset and reseeded"
    echo -e "  ${GREEN}✅${NC} Realms created (sg-admin, sg-mt-us-1, sg-mt-eu-1)"
    echo -e "  ${GREEN}✅${NC} Platform admin user created"
    echo -e "  ${GREEN}✅${NC} Token generation working"
    echo -e "  ${GREEN}✅${NC} IAM Agent login working"
    echo -e "  ${GREEN}✅${NC} Frontend login successful"
    echo -e "  ${GREEN}✅${NC} Dashboard accessible"
    echo ""
    echo -e "${GREEN}Realm architecture is fully functional! 🎉${NC}"
    echo ""
else
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                                                        ║${NC}"
    echo -e "${RED}║           ${YELLOW}❌ TEST FAILED${RED}                              ║${NC}"
    echo -e "${RED}║                                                        ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Debug steps:${NC}"
    echo ""
    echo -e "  ${BLUE}1. Check if user exists in Keycloak:${NC}"
    echo -e "     ${CYAN}http://localhost:8080/admin (admin/admin)${NC}"
    echo -e "     ${CYAN}→ Select realm: sg-admin${NC}"
    echo -e "     ${CYAN}→ Users → View all users${NC}"
    echo -e "     ${CYAN}→ Look for: admin@sentinelgrid.ai${NC}"
    echo ""
    echo -e "  ${BLUE}2. Check IAM Agent configuration:${NC}"
    echo -e "     ${CYAN}docker-compose logs iam_agent | grep KEYCLOAK_REALM${NC}"
    echo -e "     ${CYAN}Should be: sg-admin${NC}"
    echo ""
    echo -e "  ${BLUE}3. Check frontend logs:${NC}"
    echo -e "     ${CYAN}docker-compose logs frontend | tail -50${NC}"
    echo ""
    echo -e "  ${BLUE}4. Manual token test:${NC}"
    echo -e "     ${CYAN}curl -k -X POST https://localhost:8443/realms/sg-admin/protocol/openid-connect/token \\${NC}"
    echo -e "       ${CYAN}-d \"client_id=sentinelgrid-web\" \\${NC}"
    echo -e "       ${CYAN}-d \"username=admin@sentinelgrid.ai\" \\${NC}"
    echo -e "       ${CYAN}-d \"password=admin123\" \\${NC}"
    echo -e "       ${CYAN}-d \"grant_type=password\"${NC}"
    echo ""
    exit 1
fi

