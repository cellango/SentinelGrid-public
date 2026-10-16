#!/bin/bash
#
# Simple script to sync Keycloak master admin password from Vault using kcadm.sh
# No environment variables for passwords - all from Vault
#

set -e

REALM="master"
USERNAME="admin"
KEYCLOAK_CONTAINER="sentinelgrid-keycloak-1"

echo "🔄 Syncing Keycloak master admin password from Vault..."
echo ""

# Get master admin password from Vault
echo "📥 Retrieving master admin password from Vault..."
NEW_PASSWORD=$(docker exec -e VAULT_ADDR='http://127.0.0.1:8200' -e VAULT_TOKEN='sentinelgrid-dev-root-token' vault vault kv get -field=value sentinelgrid/keycloak/master-admin-password 2>/dev/null)

if [ -z "$NEW_PASSWORD" ]; then
    echo "❌ Failed to retrieve password from Vault"
    echo "   Make sure Vault is running and initialized"
    echo "   Run: backend/scripts/init_vault.sh"
    exit 1
fi

echo "✅ Retrieved password from Vault"
echo ""

# Try to authenticate with default password first, then Vault password
echo "🔐 Authenticating with Keycloak..."

# Try default password first
docker exec $KEYCLOAK_CONTAINER /opt/keycloak/bin/kcadm.sh config credentials \
    --server http://localhost:8080 \
    --realm master \
    --user admin \
    --password admin \
    > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Authenticated with default password"
    CURRENT_PASSWORD="admin"
else
    # Try Vault password
    docker exec $KEYCLOAK_CONTAINER /opt/keycloak/bin/kcadm.sh config credentials \
        --server http://localhost:8080 \
        --realm master \
        --user admin \
        --password "$NEW_PASSWORD" \
        > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✅ Authenticated with Vault password (already synced)"
        echo ""
        echo "✅ Master admin password is already synced from Vault!"
        exit 0
    else
        echo "❌ Failed to authenticate with Keycloak"
        echo "   Make sure Keycloak is running"
        exit 1
    fi
fi

echo ""

# Update password
echo "🔐 Updating master admin password in realm $REALM..."
docker exec $KEYCLOAK_CONTAINER /opt/keycloak/bin/kcadm.sh set-password \
    -r "$REALM" \
    --username "$USERNAME" \
    --new-password "$NEW_PASSWORD" \
    > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Password updated successfully!"
    echo ""
    echo "Login credentials:"
    echo "  Username: $USERNAME"
    echo "  Realm: $REALM"
    echo "  Password: (stored in Vault)"
    echo ""
    echo "⚠️  Note: You may need to reconnect with the new password for future operations"
else
    echo "❌ Failed to update password"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check if user '$USERNAME' exists in realm '$REALM'"
    echo "2. Check Keycloak logs: docker logs $KEYCLOAK_CONTAINER"
    exit 1
fi

