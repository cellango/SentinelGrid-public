#!/bin/bash
# Quick script to setup and activate a test account via API

set -e

USERNAME=${1:-admin@agribotsai.com}
PASSWORD=${2:-ChangeMe123!}
KEYCLOAK_URL=${KEYCLOAK_URL:-http://localhost:8081}
REALM=${REALM:-agribotsai}

echo "=== Keycloak Account Setup ==="
echo "Username: $USERNAME"
echo "Realm: $REALM"
echo ""

# Try API-based activation
echo "Attempting API-based activation..."
python3 << PYEOF
import sys
sys.path.insert(0, 'backend/tests')
from helpers.keycloak_account_setup import setup_test_user

success = setup_test_user(
    '$KEYCLOAK_URL',
    '$REALM',
    '$USERNAME',
    '$PASSWORD',
    'admin',
    'admin'
)

if success:
    print("✅ API activation reported success")
else:
    print("⚠️  API activation did not succeed")
PYEOF

echo ""
echo "Testing token generation..."
TOKEN_RESPONSE=$(curl -s -X POST "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=agribotsai-web" \
  -d "username=$USERNAME" \
  -d "password=$PASSWORD" \
  -d "grant_type=password" \
  -d "scope=openid")

if echo "$TOKEN_RESPONSE" | grep -q "access_token"; then
  echo "✅ Token generation SUCCESS!"
  echo ""
  echo "Access Token:"
  echo "$TOKEN_RESPONSE" | python3 -m json.tool | grep -A 1 "access_token" | head -2
else
  echo "❌ Token generation failed:"
  echo "$TOKEN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$TOKEN_RESPONSE"
  echo ""
  echo "💡 Try UI-based activation:"
  echo "   python3 scripts/activate-keycloak-account.py --username $USERNAME --password $PASSWORD --use-ui"
fi

