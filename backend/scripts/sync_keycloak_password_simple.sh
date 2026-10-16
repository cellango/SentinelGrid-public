#!/bin/bash
#
# Simple script to sync Keycloak platform admin password from Vault using kcadm.sh
# No environment variables for passwords - all from Vault
#

set -e

REALM="sg-admin"
USERNAME="admin@sentinelgrid.ai"
KEYCLOAK_CONTAINER="sentinelgrid-keycloak-1"

echo "🔄 Syncing Keycloak platform admin password from Vault..."
echo ""

# Get platform admin password from Vault
echo "📥 Retrieving platform admin password from Vault..."
PASSWORD=$(docker exec -e VAULT_ADDR='http://127.0.0.1:8200' -e VAULT_TOKEN='sentinelgrid-dev-root-token' vault vault kv get -field=value sentinelgrid/keycloak/platform-admin-password 2>/dev/null)

if [ -z "$PASSWORD" ]; then
    echo "❌ Failed to retrieve password from Vault"
    echo "   Make sure Vault is running and initialized"
    echo "   Run: backend/scripts/init_vault.sh"
    exit 1
fi

echo "✅ Retrieved password from Vault"
echo ""

# Authenticate kcadm with master realm (default admin/admin in dev mode)
echo "🔐 Authenticating with Keycloak..."
docker exec $KEYCLOAK_CONTAINER /opt/keycloak/bin/kcadm.sh config credentials \
    --server http://localhost:8080 \
    --realm master \
    --user admin \
    --password admin \
    > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "❌ Failed to authenticate with Keycloak"
    echo "   Make sure Keycloak is running"
    exit 1
fi

echo "✅ Authenticated with Keycloak"
echo ""

# Update password
echo "🔐 Updating password for $USERNAME in realm $REALM..."
docker exec $KEYCLOAK_CONTAINER /opt/keycloak/bin/kcadm.sh set-password \
    -r "$REALM" \
    --username "$USERNAME" \
    --new-password "$PASSWORD" \
    > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Password updated successfully!"
    echo ""
    echo "Login credentials:"
    echo "  Email: $USERNAME"
    echo "  Realm: $REALM"
    echo "  Password: (stored in Vault)"
else
    echo "❌ Failed to update password"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check if realm '$REALM' exists"
    echo "2. Check if user '$USERNAME' exists in realm '$REALM'"
    echo "3. Check Keycloak logs: docker logs $KEYCLOAK_CONTAINER"
    exit 1
fi

