#!/bin/bash
# Temporarily enable default admin account to create sentinelgrid-admin
# WARNING: Disable admin account again after creating sentinelgrid-admin!

set -e

echo "⚠️  WARNING: This will enable the default admin account temporarily"
echo "You MUST disable it again after creating sentinelgrid-admin!"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Get admin token using environment variables (bypasses disabled account check)
ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"

echo "Attempting to enable admin account via Keycloak REST API..."

# Try to get token and enable admin
TOKEN=$(curl -s -X POST "http://localhost:8080/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=admin-cli" \
  -d "username=admin" \
  -d "password=$ADMIN_PASSWORD" \
  -d "grant_type=password" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ] || [ "$TOKEN" = "ERROR" ]; then
    echo "❌ Cannot get admin token. The admin account is disabled."
    echo ""
    echo "Please create sentinelgrid-admin account via Keycloak Admin Console:"
    echo "1. Access: http://localhost:8081/admin"
    echo "2. If you can login, create the account manually"
    echo "3. If you cannot login, you may need to restart Keycloak with admin enabled"
    echo ""
    echo "Or use the web browser to access Keycloak and create the account."
    exit 1
fi

# Get admin user ID
ADMIN_USER_ID=$(curl -s -X GET "http://localhost:8080/admin/realms/master/users?username=admin" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | python3 -c "import sys, json; users=json.load(sys.stdin); print(users[0]['id'] if users else '')" 2>/dev/null)

if [ -z "$ADMIN_USER_ID" ]; then
    echo "❌ Could not find admin user"
    exit 1
fi

# Enable admin user
curl -s -X PUT "http://localhost:8080/admin/realms/master/users/$ADMIN_USER_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}' > /dev/null

if [ $? -eq 0 ]; then
    echo "✅ Admin account enabled temporarily"
    echo ""
    echo "Now you can:"
    echo "1. Run: ./scripts/create-sentinelgrid-admin.sh"
    echo "2. Or create the account via Keycloak Admin Console"
    echo ""
    echo "⚠️  REMEMBER: Disable the default admin account after creating sentinelgrid-admin!"
else
    echo "❌ Failed to enable admin account"
    exit 1
fi

