#!/bin/bash
# Extract the IAM Agent client secret from Keycloak
# This secret should be set in docker-compose.dev.yml as IAM_AGENT_CLIENT_SECRET

set -e

echo "=========================================="
echo "IAM Agent Client Secret Extractor"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.dev.yml"

# Step 1: Get admin token from master realm
echo -e "${YELLOW}Step 1: Getting admin token from master realm...${NC}"
ADMIN_TOKEN_RESPONSE=$(docker-compose -f $COMPOSE_FILE exec -T iam_agent curl -s -X POST http://keycloak:8080/realms/master/protocol/openid-connect/token \
  -d "client_id=admin-cli" \
  -d "username=admin" \
  -d "password=admin" \
  -d "grant_type=password" 2>/dev/null || echo "")

if ! echo "$ADMIN_TOKEN_RESPONSE" | grep -q "access_token"; then
    echo -e "${RED}❌ Failed to get admin token${NC}"
    exit 1
fi

ADMIN_TOKEN=$(echo "$ADMIN_TOKEN_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null || echo "")
echo -e "${GREEN}✅ Admin token obtained${NC}"
echo ""

# Step 2: Get sentinelgrid-iam-agent client
echo -e "${YELLOW}Step 2: Finding sentinelgrid-iam-agent client...${NC}"
CLIENTS_RESPONSE=$(docker-compose -f $COMPOSE_FILE exec -T iam_agent curl -s \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  "http://keycloak:8080/admin/realms/sentinelgrid/clients?clientId=sentinelgrid-iam-agent" 2>/dev/null || echo "")

CLIENT_ID=$(echo "$CLIENTS_RESPONSE" | python3 -c "import sys, json; clients=json.load(sys.stdin); print(clients[0]['id'] if clients else '')" 2>/dev/null || echo "")

if [ -z "$CLIENT_ID" ]; then
    echo -e "${RED}❌ Client 'sentinelgrid-iam-agent' not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Found client (ID: $CLIENT_ID)${NC}"
echo ""

# Step 3: Get client secret
echo -e "${YELLOW}Step 3: Retrieving client secret...${NC}"
SECRET_RESPONSE=$(docker-compose -f $COMPOSE_FILE exec -T iam_agent curl -s \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  "http://keycloak:8080/admin/realms/sentinelgrid/clients/$CLIENT_ID/client-secret" 2>/dev/null || echo "")

SECRET_VALUE=$(echo "$SECRET_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('value', ''))" 2>/dev/null || echo "")

if [ -z "$SECRET_VALUE" ]; then
    echo -e "${RED}❌ Failed to retrieve client secret${NC}"
    echo "Response: $SECRET_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Client secret retrieved!${NC}"
echo ""
echo "=========================================="
echo "Client Secret:"
echo "=========================================="
echo "$SECRET_VALUE"
echo ""
echo "=========================================="
echo "To use this secret, add to docker-compose.dev.yml:"
echo "=========================================="
echo ""
echo "  iam_agent:"
echo "    environment:"
echo "      - KEYCLOAK_CLIENT_SECRET=$SECRET_VALUE"
echo ""
echo "Or set in .env file:"
echo "  IAM_AGENT_CLIENT_SECRET=$SECRET_VALUE"
echo ""

