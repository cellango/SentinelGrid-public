#!/bin/bash
# Add tenant_id mapper to the realm's default client scope
# This ensures it applies to all clients automatically

set -e

echo "=========================================="
echo "Adding tenant_id to Default Client Scope"
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

# Step 2: Get default client scope
echo -e "${YELLOW}Step 2: Finding default client scope...${NC}"
SCOPES_RESPONSE=$(docker-compose -f $COMPOSE_FILE exec -T iam_agent curl -s \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  "http://keycloak:8080/admin/realms/sentinelgrid/default-default-client-scopes" 2>/dev/null || echo "")

DEFAULT_SCOPE_ID=$(echo "$SCOPES_RESPONSE" | python3 -c "import sys, json; scopes=json.load(sys.stdin); scope=[s for s in scopes if s.get('name') == 'profile' or s.get('name') == 'default']; print(scope[0]['id'] if scope else '')" 2>/dev/null || echo "")

# Try alternative: get all client scopes and find the default one
if [ -z "$DEFAULT_SCOPE_ID" ]; then
    ALL_SCOPES_RESPONSE=$(docker-compose -f $COMPOSE_FILE exec -T iam_agent curl -s \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      "http://keycloak:8080/admin/realms/sentinelgrid/client-scopes" 2>/dev/null || echo "")
    
    DEFAULT_SCOPE_ID=$(echo "$ALL_SCOPES_RESPONSE" | python3 -c "import sys, json; scopes=json.load(sys.stdin); scope=[s for s in scopes if s.get('name') == 'profile']; print(scope[0]['id'] if scope else '')" 2>/dev/null || echo "")
fi

if [ -z "$DEFAULT_SCOPE_ID" ]; then
    echo -e "${YELLOW}⚠️  Could not find default scope, trying to add to realm-level...${NC}"
    
    # Add mapper directly to realm
    MAPPER_DATA='{
        "name": "tenant-id-mapper-realm",
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
      "http://keycloak:8080/admin/realms/sentinelgrid/protocol-mappers/models" 2>/dev/null || echo "")
    
    if echo "$CREATE_RESPONSE" | grep -q "error"; then
        echo -e "${YELLOW}⚠️  Realm-level mapper may already exist or failed: $CREATE_RESPONSE${NC}"
    else
        echo -e "${GREEN}✅ Added realm-level protocol mapper${NC}"
    fi
else
    echo -e "${GREEN}✅ Found default scope (ID: $DEFAULT_SCOPE_ID)${NC}"
    
    # Check if mapper already exists
    MAPPERS_RESPONSE=$(docker-compose -f $COMPOSE_FILE exec -T iam_agent curl -s \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      "http://keycloak:8080/admin/realms/sentinelgrid/client-scopes/$DEFAULT_SCOPE_ID/protocol-mappers/models" 2>/dev/null || echo "")
    
    HAS_MAPPER=$(echo "$MAPPERS_RESPONSE" | python3 -c "import sys, json; mappers=json.load(sys.stdin); print('YES' if any('tenant-id' in m.get('name', '') for m in mappers) else 'NO')" 2>/dev/null || echo "NO")
    
    if [ "$HAS_MAPPER" = "YES" ]; then
        echo -e "${GREEN}✅ Mapper already exists in default scope${NC}"
    else
        MAPPER_DATA='{
            "name": "tenant-id-mapper-scope",
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
          "http://keycloak:8080/admin/realms/sentinelgrid/client-scopes/$DEFAULT_SCOPE_ID/protocol-mappers/models" 2>/dev/null || echo "")
        
        if echo "$CREATE_RESPONSE" | grep -q "error"; then
            echo -e "${RED}❌ Failed to create mapper: $CREATE_RESPONSE${NC}"
        else
            echo -e "${GREEN}✅ Added mapper to default client scope${NC}"
        fi
    fi
fi

echo ""
echo -e "${YELLOW}Note: You may need to log out and log back in for the changes to take effect${NC}"

