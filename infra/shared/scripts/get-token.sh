#!/bin/bash
# Get JWT Token from Keycloak
# Usage: ./get-token.sh <realm> <client-id> <username> <password> [keycloak-url]

REALM=${1:-"agribotsai"}
CLIENT_ID=${2:-"agribotsai-web"}
USERNAME=${3:-"admin@agribotsai.com"}
PASSWORD=${4:-"ChangeMe123!"}
KEYCLOAK_URL=${5:-"http://localhost:8081"}

TOKEN_ENDPOINT="$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token"

echo "Getting token for $USERNAME in realm $REALM..."

RESPONSE=$(curl -s -X POST "$TOKEN_ENDPOINT" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=$CLIENT_ID" \
  -d "username=$USERNAME" \
  -d "password=$PASSWORD" \
  -d "grant_type=password")

if echo "$RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
  echo "❌ Error getting token:"
  echo "$RESPONSE" | jq '.'
  exit 1
fi

ACCESS_TOKEN=$(echo "$RESPONSE" | jq -r '.access_token')
REFRESH_TOKEN=$(echo "$RESPONSE" | jq -r '.refresh_token')

if [ "$ACCESS_TOKEN" != "null" ] && [ ! -z "$ACCESS_TOKEN" ]; then
  echo ""
  echo "✅ Token obtained successfully!"
  echo ""
  echo "Access Token:"
  echo "$ACCESS_TOKEN"
  echo ""
  echo "Decoded Token Claims:"
  echo "$ACCESS_TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | jq '.' || echo "$ACCESS_TOKEN" | cut -d. -f2 | python3 -m base64 -d 2>/dev/null | python3 -m json.tool
  echo ""
  echo "Refresh Token:"
  echo "$REFRESH_TOKEN"
  echo ""
  echo "💡 To use this token:"
  echo "export TOKEN=\"$ACCESS_TOKEN\""
  echo "curl -H \"Authorization: Bearer \$TOKEN\" http://localhost:8080/api/v1/alerts"
else
  echo "❌ Failed to extract token from response"
  echo "$RESPONSE" | jq '.'
  exit 1
fi

