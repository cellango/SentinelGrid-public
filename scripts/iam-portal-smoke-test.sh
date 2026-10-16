#!/bin/bash
# End-to-end smoke test for IAM Portal APIs.
#
# This script:
# 1. Gets an admin token from Keycloak via the iam_agent container
# 2. Calls IAM Portal APIs on localhost:8005
#    - Lists users
#    - Creates a test user
#    - Lists users again to confirm creation

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo " IAM Portal Smoke Test"
echo "=========================================="
echo ""

COMPOSE_FILE="docker-compose.dev.yml"

echo -e "${YELLOW}Step 1: Getting admin token from Keycloak...${NC}"

TOKEN=$(
  docker-compose -f "$COMPOSE_FILE" exec -T iam_agent \
    curl -s -X POST http://keycloak:8080/realms/sentinelgrid/protocol/openid-connect/token \
      -d "client_id=sentinelgrid-web" \
      -d "username=admin@sentinelgrid.ai" \
      -d "password=admin123" \
      -d "grant_type=password" | \
    python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null
)

if [ -z "$TOKEN" ] || [ ${#TOKEN} -lt 100 ]; then
  echo -e "${RED}❌ Failed to obtain admin access token${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Obtained admin token${NC}"
echo ""

API_BASE="http://localhost:8005/api/iam-portal"

echo -e "${YELLOW}Step 2: Listing users (before)...${NC}"
curl -s -H "Authorization: Bearer $TOKEN" "$API_BASE/users" | python3 -m json.tool || true
echo ""

echo -e "${YELLOW}Step 3: Creating test user...${NC}"

# Use a unique username each run to avoid Keycloak 409 conflicts
TS=$(date +%s)
RND=$RANDOM
TEST_USERNAME="employee-${TS}-${RND}@example.com"

CREATE_RESPONSE=$(
  curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$API_BASE/users" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"${TEST_USERNAME}\",
      \"email\": \"${TEST_USERNAME}\",
      \"first_name\": \"Employee\",
      \"last_name\": \"SmokeTest\",
      \"department\": \"Engineering\"
    }"
)

HTTP_CODE=$(echo "$CREATE_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$CREATE_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "201" ]; then
  echo -e "${RED}❌ Failed to create user (HTTP $HTTP_CODE)${NC}"
  echo "Response:"
  echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
  exit 1
fi

echo -e "${GREEN}✅ User creation API succeeded (HTTP $HTTP_CODE)${NC}"
echo "Response:"
echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
echo ""

echo -e "${YELLOW}Step 4: Listing users (after)...${NC}"
curl -s -H "Authorization: Bearer $TOKEN" "$API_BASE/users" | python3 -m json.tool || true
echo ""

echo "=========================================="
echo -e "${GREEN}IAM Portal smoke test completed.${NC}"
echo "=========================================="
echo ""


