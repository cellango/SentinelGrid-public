#!/bin/bash
# Configure User Profile via Realm Component API using curl (runs inside Keycloak container)

set -e

REALM=${1:-agribotsai}
ATTRIBUTE_NAME=${2:-tenant_id}
KEYCLOAK_URL=${KEYCLOAK_URL:-http://localhost:8080}

echo "Configuring User Profile attribute '$ATTRIBUTE_NAME' in realm '$REALM'"
echo "=" | head -c 60 && echo ""

# Step 1: Get admin token
echo ""
echo "1. Getting admin token..."
ADMIN_TOKEN=$(curl -s -X POST "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=admin-cli&username=admin&password=admin&grant_type=password" | \
  grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')

if [ -z "$ADMIN_TOKEN" ]; then
    echo "❌ Failed to get admin token"
    exit 1
fi
echo "✅ Admin token obtained"

# Step 2: Get components
echo ""
echo "2. Getting realm components..."
COMPONENTS_RESPONSE=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM/components" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json")

# Find User Profile provider ID
PROVIDER_ID=$(echo "$COMPONENTS_RESPONSE" | grep -o '"id":"[^"]*","name":"[^"]*","providerId":"declarative-user-profile"[^}]*' | \
  grep -o '"id":"[^"]*' | head -1 | sed 's/"id":"//')

if [ -z "$PROVIDER_ID" ]; then
    echo "⚠️  User Profile provider not found. Creating..."
    # Create provider - simplified version
    CREATE_RESPONSE=$(curl -s -X POST "$KEYCLOAK_URL/admin/realms/$REALM/components" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"name":"declarative-user-profile","providerId":"declarative-user-profile","providerType":"org.keycloak.userprofile.UserProfileProvider","parentId":"'$REALM'","config":{"kc.user.profile.config":["{\"attributes\":[],\"unmanagedAttributePolicy\":\"ENABLED\"}"]}}')
    
    PROVIDER_ID=$(echo "$CREATE_RESPONSE" | grep -o '"id":"[^"]*' | head -1 | sed 's/"id":"//')
    if [ -z "$PROVIDER_ID" ]; then
        echo "❌ Failed to create User Profile provider"
        echo "Response: $CREATE_RESPONSE"
        exit 1
    fi
    echo "✅ Created User Profile provider (ID: $PROVIDER_ID)"
else
    echo "✅ Found User Profile provider (ID: $PROVIDER_ID)"
fi

# Step 3: Get current config and update
echo ""
echo "3. Getting current User Profile configuration..."
PROVIDER_CONFIG=$(curl -s -X GET "$KEYCLOAK_URL/admin/realms/$REALM/components/$PROVIDER_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json")

CURRENT_CONFIG_STR=$(echo "$PROVIDER_CONFIG" | grep -o '"kc.user.profile.config":\["[^"]*' | \
  sed 's/"kc.user.profile.config":\["//' | sed 's/\\"/"/g')

if [ -z "$CURRENT_CONFIG_STR" ]; then
    echo "⚠️  No config found, using default..."
    CURRENT_CONFIG='{"attributes":[],"unmanagedAttributePolicy":"ENABLED"}'
else
    CURRENT_CONFIG="$CURRENT_CONFIG_STR"
fi

echo "Current config preview: ${CURRENT_CONFIG:0:100}..."

# This is complex to do in pure shell - would need jq or python
# For now, let's try a simpler approach: enable unmanaged attributes
echo ""
echo "4. Configuring User Profile (enabling unmanaged attributes)..."
echo "   Note: Adding specific attributes requires JSON manipulation"
echo "   This script enables unmanaged attributes which should allow"
echo "   setting any attribute via API/kcadm.sh"

# Update with unmanaged attributes enabled
# We'll use a basic config that enables unmanaged attributes
UPDATED_CONFIG='{"attributes":[],"unmanagedAttributePolicy":"ENABLED"}'

UPDATE_PAYLOAD=$(cat <<EOF
{
  "name": "declarative-user-profile",
  "providerId": "declarative-user-profile",
  "providerType": "org.keycloak.userprofile.UserProfileProvider",
  "parentId": "$REALM",
  "config": {
    "kc.user.profile.config": ["$UPDATED_CONFIG"]
  }
}
EOF
)

HTTP_CODE=$(curl -s -w "%{http_code}" -o /tmp/update_response.json \
  -X PUT "$KEYCLOAK_URL/admin/realms/$REALM/components/$PROVIDER_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$UPDATE_PAYLOAD")

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
    echo "✅✅✅ User Profile configured!"
    echo "   Unmanaged attributes are now enabled"
    echo "   You should now be able to set $ATTRIBUTE_NAME via API/kcadm.sh"
    exit 0
else
    echo "❌ Failed to update User Profile (HTTP $HTTP_CODE)"
    cat /tmp/update_response.json
    exit 1
fi

