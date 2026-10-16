#!/bin/bash
#
# Sync Keycloak Platform Admin Password from Vault
# 
# This script retrieves the platform admin password from Vault and updates
# the corresponding user in Keycloak to match.
#

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-sentinelgrid-dev-root-token}"
KEYCLOAK_CONTAINER="keycloak"
REALM="sg-admin"
USERNAME="admin@sentinelgrid.ai"

echo -e "${YELLOW}Syncing Keycloak platform admin password from Vault...${NC}"
echo ""

# Step 1: Get password from Vault
echo "📥 Retrieving password from Vault..."
PASSWORD=$(docker exec -e VAULT_ADDR="$VAULT_ADDR" -e VAULT_TOKEN="$VAULT_TOKEN" vault vault kv get -field=value sentinelgrid/keycloak/platform-admin-password 2>/dev/null)

if [ -z "$PASSWORD" ]; then
    echo -e "${RED}❌ Failed to retrieve password from Vault${NC}"
    echo "   Make sure Vault is running and initialized"
    echo "   Run: backend/scripts/init_vault.sh"
    exit 1
fi

echo -e "${GREEN}✅ Retrieved password from Vault${NC}"
echo ""

# Step 2: Check if Keycloak container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${KEYCLOAK_CONTAINER}$"; then
    echo -e "${RED}❌ Keycloak container '${KEYCLOAK_CONTAINER}' is not running${NC}"
    echo "   Start it with: docker-compose -f docker-compose.dev.yml up -d keycloak"
    exit 1
fi

echo -e "${GREEN}✅ Keycloak container is running${NC}"
echo ""

# Step 3: Update password in Keycloak using kcadm
echo "🔐 Updating password in Keycloak..."
echo "   Realm: $REALM"
echo "   Username: $USERNAME"
echo ""

# Use kcadm to set password (escape special characters)
# Note: We need to authenticate first
KEYCLOAK_ADMIN_USER="${KEYCLOAK_ADMIN_USER:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"

# Authenticate kcadm
docker exec $KEYCLOAK_CONTAINER /opt/keycloak/bin/kcadm.sh config credentials \
    --server http://localhost:8080 \
    --realm master \
    --user "$KEYCLOAK_ADMIN_USER" \
    --password "$KEYCLOAK_ADMIN_PASSWORD" \
    > /dev/null 2>&1 || {
    echo -e "${YELLOW}⚠️  Could not authenticate with Keycloak admin credentials${NC}"
    echo "   Trying to set password anyway..."
}

# Set password (escape special characters in password)
# Use single quotes and escape within the container
docker exec $KEYCLOAK_CONTAINER /opt/keycloak/bin/kcadm.sh set-password \
    -r "$REALM" \
    --username "$USERNAME" \
    --new-password "$PASSWORD" \
    > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Successfully updated Keycloak password${NC}"
    echo ""
    echo -e "${GREEN}Password synced!${NC}"
    echo "   Email: $USERNAME"
    echo "   Realm: $REALM"
    echo ""
    echo "You can now log in with the password from Vault."
else
    echo -e "${RED}❌ Failed to update password in Keycloak${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check if realm '$REALM' exists"
    echo "2. Check if user '$USERNAME' exists in realm '$REALM'"
    echo "3. Verify Keycloak admin credentials"
    exit 1
fi

