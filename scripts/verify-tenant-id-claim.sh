#!/bin/bash
# Verify that tenant_id claim is present in JWT tokens
# This script tests if the protocol mapper is working correctly

set -e

echo "=========================================="
echo "Tenant ID Claim Verification"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.dev.yml"

# Step 1: Get admin token
echo -e "${YELLOW}Step 1: Getting admin token...${NC}"
TOKEN_RESPONSE=$(docker-compose -f $COMPOSE_FILE exec -T iam_agent curl -s -X POST http://keycloak:8080/realms/sentinelgrid/protocol/openid-connect/token \
  -d "client_id=sentinelgrid-web" \
  -d "username=admin@sentinelgrid.ai" \
  -d "password=admin123" \
  -d "grant_type=password" 2>/dev/null || echo "")

if ! echo "$TOKEN_RESPONSE" | grep -q "access_token"; then
    echo -e "${RED}❌ Failed to get token${NC}"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null || echo "")

if [ -z "$TOKEN" ] || [ ${#TOKEN} -lt 100 ]; then
    echo -e "${RED}❌ Invalid token${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Token obtained${NC}"
echo ""

# Step 2: Decode token and check for tenant_id
echo -e "${YELLOW}Step 2: Decoding token and checking for tenant_id claim...${NC}"
PAYLOAD=$(echo "$TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "")

if [ -z "$PAYLOAD" ]; then
    echo -e "${RED}❌ Failed to decode token payload${NC}"
    exit 1
fi

# Check if tenant_id is present
if echo "$PAYLOAD" | grep -q '"tenant_id"'; then
    TENANT_ID_VALUE=$(echo "$PAYLOAD" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('tenant_id', 'NOT_FOUND'))" 2>/dev/null || echo "NOT_FOUND")
    if [ "$TENANT_ID_VALUE" != "NOT_FOUND" ] && [ -n "$TENANT_ID_VALUE" ]; then
        echo -e "${GREEN}✅ tenant_id claim is present in token!${NC}"
        echo "   Value: $TENANT_ID_VALUE"
        echo ""
        echo "Full token payload:"
        echo "$PAYLOAD" | python3 -m json.tool
        echo ""
        echo -e "${GREEN}✅ Protocol mapper is working correctly!${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠️  tenant_id key exists but value is empty${NC}"
    fi
else
    echo -e "${RED}❌ tenant_id claim is NOT present in token${NC}"
    echo ""
    echo "Token payload (showing all claims):"
    echo "$PAYLOAD" | python3 -m json.tool
    echo ""
    echo -e "${YELLOW}⚠️  Protocol mapper may not be configured correctly${NC}"
    echo "   Check Keycloak Admin Console: http://localhost:8081/admin"
    echo "   Realm: sentinelgrid"
    echo "   Clients → sentinelgrid-web → Client Scopes → Mappers"
    echo "   Look for 'tenant-id-mapper'"
    exit 1
fi

