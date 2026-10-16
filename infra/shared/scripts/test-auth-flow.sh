#!/bin/bash
# End-to-End Authentication Flow Test
# Tests: Keycloak → IAM Agent → API Gateway

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEYCLOAK_URL=${1:-"http://localhost:8081"}
REALM=${2:-"agribotsai"}
USERNAME=${3:-"admin@agribotsai.com"}
PASSWORD=${4:-"ChangeMe123!"}
IAM_AGENT_URL=${5:-"http://localhost:8005"}
API_GATEWAY_URL=${6:-"http://localhost:8080"}

echo "=========================================="
echo "End-to-End Authentication Flow Test"
echo "=========================================="
echo "Realm: $REALM"
echo "Username: $USERNAME"
echo "Keycloak: $KEYCLOAK_URL"
echo "IAM Agent: $IAM_AGENT_URL"
echo "API Gateway: $API_GATEWAY_URL"
echo ""

# Step 1: Get token from Keycloak
echo "Step 1: Getting token from Keycloak..."
TOKEN_ENDPOINT="$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token"
RESPONSE=$(curl -s -X POST "$TOKEN_ENDPOINT" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=$REALM-web" \
  -d "username=$USERNAME" \
  -d "password=$PASSWORD" \
  -d "grant_type=password")

if echo "$RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
  echo "❌ Failed to get token"
  echo "$RESPONSE" | jq '.'
  exit 1
fi

ACCESS_TOKEN=$(echo "$RESPONSE" | jq -r '.access_token')
if [ "$ACCESS_TOKEN" == "null" ] || [ -z "$ACCESS_TOKEN" ]; then
  echo "❌ No access token in response"
  exit 1
fi

echo "✅ Token obtained"
echo ""

# Step 2: Decode token to show claims
echo "Step 2: Decoding token claims..."
TOKEN_CLAIMS=$(echo "$ACCESS_TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | jq '.' || echo "$ACCESS_TOKEN" | cut -d. -f2 | python3 -m base64 -d 2>/dev/null | python3 -m json.tool)
echo "$TOKEN_CLAIMS" | jq '.'
echo ""

# Extract tenant_id and roles
TENANT_ID=$(echo "$TOKEN_CLAIMS" | jq -r '.tenant_id // "not found"')
ROLES=$(echo "$TOKEN_CLAIMS" | jq -r '.realm_access.roles[]? // []')
echo "Tenant ID: $TENANT_ID"
echo "Roles: $ROLES"
echo ""

# Step 3: Test IAM Agent validation
echo "Step 3: Testing IAM Agent token validation..."
IAM_RESPONSE=$(curl -s -X POST "$IAM_AGENT_URL/internal/iam/auth/validate-token" \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"$ACCESS_TOKEN\"}")

IAM_VALID=$(echo "$IAM_RESPONSE" | jq -r '.valid // false')
IAM_TENANT_ID=$(echo "$IAM_RESPONSE" | jq -r '.tenant_id // "not found"')
IAM_ROLES=$(echo "$IAM_RESPONSE" | jq -r '.roles[]? // []')

if [ "$IAM_VALID" == "true" ]; then
  echo "✅ IAM Agent validation successful"
  echo "   Tenant ID: $IAM_TENANT_ID"
  echo "   Roles: $IAM_ROLES"
else
  echo "❌ IAM Agent validation failed"
  echo "$IAM_RESPONSE" | jq '.'
  exit 1
fi
echo ""

# Step 4: Test API Gateway
echo "Step 4: Testing API Gateway with token..."
API_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_GATEWAY_URL/api/v1/alerts" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

HTTP_CODE=$(echo "$API_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
API_BODY=$(echo "$API_RESPONSE" | sed '/HTTP_CODE:/d')

if [ "$HTTP_CODE" == "200" ]; then
  echo "✅ API Gateway request successful"
  echo "$API_BODY" | jq '.' | head -20
else
  echo "⚠️  API Gateway returned HTTP $HTTP_CODE"
  echo "$API_BODY" | jq '.' || echo "$API_BODY"
fi
echo ""

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "✅ Keycloak token generation: PASS"
echo "$([ "$IAM_VALID" == "true" ] && echo '✅' || echo '❌') IAM Agent validation: $([ "$IAM_VALID" == "true" ] && echo 'PASS' || echo 'FAIL')"
echo "$([ "$HTTP_CODE" == "200" ] && echo '✅' || echo '⚠️') API Gateway integration: HTTP $HTTP_CODE"
echo ""
echo "Tenant ID Extraction: $([ "$IAM_TENANT_ID" != "not found" ] && echo "✅ Found: $IAM_TENANT_ID" || echo "❌ Not found")"
echo "Roles Extraction: $([ ! -z "$IAM_ROLES" ] && echo "✅ Found: $IAM_ROLES" || echo "❌ Not found")"

