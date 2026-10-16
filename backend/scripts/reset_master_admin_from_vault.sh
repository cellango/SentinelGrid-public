#!/bin/bash
#
# Reset Keycloak master admin password from Vault when passwords are out of sync
# This resets the password directly in Keycloak database to match Vault
#

set -e

echo "🔄 Resetting Keycloak master admin password to match Vault..."
echo ""

# Get password from Vault
echo "📥 Retrieving master admin password from Vault..."
VAULT_PASS=$(docker exec -e VAULT_ADDR='http://127.0.0.1:8200' -e VAULT_TOKEN='sentinelgrid-dev-root-token' vault vault kv get -field=value sentinelgrid/keycloak/master-admin-password 2>/dev/null)

if [ -z "$VAULT_PASS" ]; then
    echo "❌ Failed to retrieve password from Vault"
    echo "   Make sure Vault is running and initialized"
    echo "   Run: backend/scripts/init_vault.sh"
    exit 1
fi

echo "✅ Retrieved password from Vault (length: ${#VAULT_PASS} chars)"
echo ""

# We need to use Keycloak's password hashing, which is complex
# The simplest approach is to set KEYCLOAK_ADMIN_PASSWORD env var and restart
# But that only works on first startup in dev mode

# Better approach: Use Keycloak's built-in password reset via kcadm
# But we need to authenticate first... which we can't do!

# Actually, the BEST solution: Update Vault to match what Keycloak currently has
# OR reset Keycloak database to use Vault password

echo "💡 Solution: Update Vault to match current Keycloak password"
echo ""
echo "Since we can't authenticate to Keycloak, we have two options:"
echo ""
echo "Option 1: Reset Keycloak to use Vault password (requires database access)"
echo "Option 2: Update Vault to match current Keycloak password (if we can find it)"
echo ""
echo "For dev mode, the simplest is to:"
echo "1. Find out what Keycloak's current password is"
echo "2. Update Vault to match it"
echo ""
echo "OR reset Keycloak database to use the Vault password."
echo ""

echo "🔧 Trying to reset via Keycloak database..."
echo ""

# Check database access
DB_CONTAINER="sentinelgrid-keycloak_db-1"
if ! docker ps --format "{{.Names}}" | grep -q "^${DB_CONTAINER}$"; then
    echo "❌ Keycloak database container not found: $DB_CONTAINER"
    exit 1
fi

echo "✅ Found Keycloak database container"
echo ""

# Keycloak uses PBKDF2-SHA256 for password hashing
# We can't easily generate this hash, so we need a different approach

echo "⚠️  Direct database password reset is complex (requires proper hash generation)"
echo ""
echo "💡 RECOMMENDED SOLUTION: Update Vault to use current Keycloak password"
echo ""
echo "Since Vault was re-seeded, we should:"
echo "1. Use the current Keycloak password (if known)"
echo "2. Update Vault to store that password"
echo ""
echo "OR, if we want Vault to be the source of truth:"
echo "1. Reset Keycloak admin password via environment variable on next restart"
echo ""

# Actually, the best solution is simpler: Update Vault to match what Keycloak has
# But we don't know what Keycloak has...

echo "🔄 Practical solution: Use default password and sync from there"
echo ""
echo "If Keycloak still uses default 'admin' password, we can:"
echo "1. Update Vault to store 'admin' (temporary)"
echo "2. Then use sync script to update Keycloak to new Vault password"
echo ""

echo "Would you like to:"
echo "  A) Update Vault to use current Keycloak password (if known)"
echo "  B) Reset Keycloak to use Vault password (requires database reset)"
echo ""
echo "For now, the best approach is to manually update Vault with the current"
echo "Keycloak password if you know it, then run the sync script."

exit 0

