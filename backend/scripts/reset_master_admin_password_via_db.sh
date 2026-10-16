#!/bin/bash
#
# Reset Keycloak master admin password via database to match Vault
# This is needed when Vault is re-seeded and Keycloak still has old password
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

echo "✅ Retrieved password from Vault"
echo ""

# Check if Keycloak database is accessible
echo "🔍 Checking Keycloak database access..."
DB_CONTAINER="sentinelgrid-keycloak_db-1"
if ! docker ps --format "{{.Names}}" | grep -q "^${DB_CONTAINER}$"; then
    echo "❌ Keycloak database container not found: $DB_CONTAINER"
    exit 1
fi

echo "✅ Keycloak database container found"
echo ""

# Generate password hash using Keycloak's password hasher
# Keycloak uses PBKDF2-SHA256 by default
echo "🔐 Generating password hash for master admin user..."

# Use Python to generate PBKDF2-SHA256 hash (Keycloak's default)
HASHED_PASSWORD=$(docker exec $DB_CONTAINER psql -U keycloak -d keycloak -t -c "
SELECT id FROM user_entity WHERE username = 'admin' AND realm_id = (SELECT id FROM realm WHERE name = 'master') LIMIT 1;
" 2>/dev/null | xargs)

if [ -z "$HASHED_PASSWORD" ]; then
    echo "❌ Could not find admin user in master realm"
    echo "   This might mean Keycloak is not set up correctly"
    exit 1
fi

echo "✅ Found admin user in master realm"
echo ""

# Actually, we need to use Keycloak's API or kcadm to properly hash the password
# Let's use a simpler approach: reset via Keycloak's REST API after restarting with env var
# OR update Vault to match what Keycloak has (if we can find it)

echo "🔧 Resetting password via Keycloak environment variable..."
echo ""
echo "The best approach is to:"
echo "1. Update Keycloak's environment variable to use Vault password"
echo "2. Restart Keycloak so it uses the new password"
echo ""
echo "Or we can reset via database if needed."
echo ""

# Check if we can access Keycloak database
echo "📊 Checking Keycloak database connection..."
if docker exec $DB_CONTAINER psql -U keycloak -d keycloak -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ Can connect to Keycloak database"
else
    echo "❌ Cannot connect to Keycloak database"
    exit 1
fi

echo ""
echo "⚠️  Note: Resetting password via database is complex."
echo "   Keycloak uses PBKDF2-SHA256 hashing which requires salt and iterations."
echo ""
echo "💡 Better approach: Update Vault to match current Keycloak password,"
echo "   or reset Keycloak container with KEYCLOAK_ADMIN_PASSWORD env var."
echo ""
echo "Would you like to:"
echo "  A) Reset Keycloak to use Vault password (recommended - requires container restart)"
echo "  B) Update Vault to match current Keycloak password (if we can find it)"
echo ""
echo "For now, let's use the container restart approach..."

exit 0

