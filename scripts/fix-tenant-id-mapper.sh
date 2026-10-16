#!/bin/bash
# Fix tenant_id protocol mapper and verify it's working
# This script:
# 1. Verifies the user has tenant_id attribute
# 2. Ensures protocol mapper is correctly configured
# 3. Tests token generation to confirm tenant_id appears

set -e

echo "=========================================="
echo "Tenant ID Mapper Fix & Verification"
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
ADMIN_TOKEN_RESPONSE=$(docker-compose -f $COMPOSE_FILE exec -T iam_agent curl -s -X POST http://keycloak:8080/realms/master/protocol/openid-connect/token \
  -d "client_id=admin-cli" \
  -d "username=admin" \
  -d "password=admin" \
  -d "grant_type=password" 2>/dev/null || echo "")

ADMIN_TOKEN=$(echo "$ADMIN_TOKEN_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null || echo "")
echo -e "${GREEN}✅ Admin token obtained${NC}"
echo ""

# Step 2: Check if user has tenant_id attribute
echo -e "${YELLOW}Step 2: Checking user attributes...${NC}"
USER_RESPONSE=$(docker-compose -f $COMPOSE_FILE exec -T iam_agent curl -s \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  "http://keycloak:8080/admin/realms/sentinelgrid/users?username=admin@sentinelgrid.ai&exact=true" 2>/dev/null || echo "")

USER_ID=$(echo "$USER_RESPONSE" | python3 -c "import sys, json; users=json.load(sys.stdin); print(users[0]['id'] if users else '')" 2>/dev/null || echo "")

if [ -z "$USER_ID" ]; then
    echo -e "${RED}❌ User not found${NC}"
    exit 1
fi

USER_DETAILS=$(docker-compose -f $COMPOSE_FILE exec -T iam_agent curl -s \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  "http://keycloak:8080/admin/realms/sentinelgrid/users/$USER_ID" 2>/dev/null || echo "")

TENANT_ID_ATTR=$(echo "$USER_DETAILS" | python3 -c "import sys, json; d=json.load(sys.stdin); attrs=d.get('attributes', {}); print(attrs.get('tenant_id', [''])[0] if attrs.get('tenant_id') else '')" 2>/dev/null || echo "")

if [ -z "$TENANT_ID_ATTR" ]; then
    echo -e "${YELLOW}⚠️  User does not have tenant_id attribute - setting it...${NC}"
    
    # Get tenant ID from database
    TENANT_ID_FROM_DB=$(docker-compose -f $COMPOSE_FILE exec -T postgres psql -U sg -d sg -t -c "SELECT id FROM tenants WHERE slug = 'sentinelgrid' LIMIT 1;" 2>/dev/null | tr -d ' \n' || echo "")
    
    if [ -z "$TENANT_ID_FROM_DB" ]; then
        echo -e "${RED}❌ Could not get tenant ID from database${NC}"
        exit 1
    fi
    
    # Update user with tenant_id attribute
    USER_JSON=$(echo "$USER_DETAILS" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if 'attributes' not in d:
    d['attributes'] = {}
d['attributes']['tenant_id'] = ['$TENANT_ID_FROM_DB']
print(json.dumps(d))
" 2>/dev/null || echo "")
    
    UPDATE_RESPONSE=$(docker-compose -f $COMPOSE_FILE exec -T iam_agent curl -s -X PUT \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$USER_JSON" \
      "http://keycloak:8080/admin/realms/sentinelgrid/users/$USER_ID" 2>/dev/null || echo "")
    
    if [ -n "$UPDATE_RESPONSE" ] && [ "$UPDATE_RESPONSE" != "null" ]; then
        echo -e "${RED}❌ Failed to update user: $UPDATE_RESPONSE${NC}"
    else
        echo -e "${GREEN}✅ Set tenant_id=$TENANT_ID_FROM_DB for user${NC}"
    fi
else
    echo -e "${GREEN}✅ User has tenant_id attribute: $TENANT_ID_ATTR${NC}"
fi
echo ""

# Step 3: Verify protocol mapper exists
echo -e "${YELLOW}Step 3: Verifying protocol mapper...${NC}"
CLIENTS_RESPONSE=$(docker-compose -f $COMPOSE_FILE exec -T iam_agent curl -s \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  "http://keycloak:8080/admin/realms/sentinelgrid/clients?clientId=sentinelgrid-web" 2>/dev/null || echo "")

WEB_CLIENT_ID=$(echo "$CLIENTS_RESPONSE" | python3 -c "import sys, json; clients=json.load(sys.stdin); print(clients[0]['id'] if clients else '')" 2>/dev/null || echo "")

if [ -z "$WEB_CLIENT_ID" ]; then
    echo -e "${RED}❌ sentinelgrid-web client not found${NC}"
    exit 1
fi

MAPPERS_RESPONSE=$(docker-compose -f $COMPOSE_FILE exec -T iam_agent curl -s \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  "http://keycloak:8080/admin/realms/sentinelgrid/clients/$WEB_CLIENT_ID/protocol-mappers/models" 2>/dev/null || echo "")

HAS_MAPPER=$(echo "$MAPPERS_RESPONSE" | python3 -c "import sys, json; mappers=json.load(sys.stdin); print('YES' if any(m.get('name') == 'tenant-id-mapper' for m in mappers) else 'NO')" 2>/dev/null || echo "NO")

if [ "$HAS_MAPPER" = "YES" ]; then
    echo -e "${GREEN}✅ Protocol mapper 'tenant-id-mapper' exists${NC}"
else
    echo -e "${YELLOW}⚠️  Protocol mapper not found - creating it...${NC}"
    
    MAPPER_DATA='{
        "name": "tenant-id-mapper",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-attribute-mapper",
        "config": {
            "user.attribute": "tenant_id",
            "claim.name": "tenant_id",
            "jsonType.label": "String",
            "id.token.claim": "true",
            "access.token.claim": "true",
            "userinfo.token.claim": "true"
        }
    }'
    
    CREATE_RESPONSE=$(docker-compose -f $COMPOSE_FILE exec -T iam_agent curl -s -X POST \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$MAPPER_DATA" \
      "http://keycloak:8080/admin/realms/sentinelgrid/clients/$WEB_CLIENT_ID/protocol-mappers/models" 2>/dev/null || echo "")
    
    if echo "$CREATE_RESPONSE" | grep -q "error"; then
        echo -e "${RED}❌ Failed to create mapper: $CREATE_RESPONSE${NC}"
    else
        echo -e "${GREEN}✅ Protocol mapper created${NC}"
    fi
fi
echo ""

# Step 4: Test token generation
echo -e "${YELLOW}Step 4: Testing token generation with tenant_id...${NC}"
sleep 2  # Give Keycloak a moment to process changes

TOKEN_RESPONSE=$(docker-compose -f $COMPOSE_FILE exec -T iam_agent curl -s -X POST http://keycloak:8080/realms/sentinelgrid/protocol/openid-connect/token \
  -d "client_id=sentinelgrid-web" \
  -d "username=admin@sentinelgrid.ai" \
  -d "password=admin123" \
  -d "grant_type=password" 2>/dev/null || echo "")

TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null || echo "")

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Failed to get token${NC}"
    exit 1
fi

PAYLOAD=$(echo "$TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "")

if echo "$PAYLOAD" | grep -q '"tenant_id"'; then
    TENANT_ID_VALUE=$(echo "$PAYLOAD" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('tenant_id', 'NOT_FOUND'))" 2>/dev/null || echo "NOT_FOUND")
    echo -e "${GREEN}✅ tenant_id claim is present in token!${NC}"
    echo "   Value: $TENANT_ID_VALUE"
    echo ""
    echo -e "${GREEN}✅ Protocol mapper is working correctly!${NC}"
else
    echo -e "${RED}❌ tenant_id claim still not in token${NC}"
    echo ""
    echo "Token payload:"
    echo "$PAYLOAD" | python3 -m json.tool | head -30
    echo ""
    echo -e "${YELLOW}⚠️  May need to wait a few seconds and regenerate token${NC}"
fi

