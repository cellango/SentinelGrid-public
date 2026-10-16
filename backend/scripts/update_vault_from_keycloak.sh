#!/bin/bash
#
# Update Vault with Keycloak's current master admin password
# Use this when you know Keycloak's password but Vault has a different one
#

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <current-keycloak-password>"
    echo ""
    echo "This updates Vault to match Keycloak's current master admin password."
    echo ""
    echo "Example:"
    echo "  $0 admin"
    exit 1
fi

CURRENT_PASSWORD="$1"

echo "🔄 Updating Vault to match Keycloak's current password..."
echo ""

# Update Vault
echo "📝 Updating Vault with current Keycloak password..."
docker exec -e VAULT_ADDR='http://127.0.0.1:8200' \
  -e VAULT_TOKEN='sentinelgrid-dev-root-token' \
  vault vault kv put sentinelgrid/keycloak/master-admin-password value="$CURRENT_PASSWORD"

if [ $? -eq 0 ]; then
    echo "✅ Vault updated successfully!"
    echo ""
    echo "Passwords are now in sync!"
    echo "  Keycloak: $CURRENT_PASSWORD"
    echo "  Vault: $CURRENT_PASSWORD"
    echo ""
    echo "You can now use the sync scripts to keep them in sync in the future."
else
    echo "❌ Failed to update Vault"
    exit 1
fi

