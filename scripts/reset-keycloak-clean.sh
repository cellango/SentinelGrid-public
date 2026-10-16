#!/bin/bash
# Clean reset of Keycloak database
# This removes all Keycloak data and starts fresh with default admin/admin

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=" * 70
echo "⚠️  KEYCLOAK DATABASE RESET - THIS WILL DELETE ALL KEYCLOAK DATA"
echo "=" * 70
echo ""
echo "This will:"
echo "  ❌ Delete all realms (master realm will be recreated)"
echo "  ❌ Delete all users (except new admin user)"
echo "  ❌ Delete all clients and configurations"
echo "  ✅ Keep SentinelGrid database (tenants, apps, etc.)"
echo "  ✅ Recreate Keycloak with default admin/admin credentials"
echo ""

# Confirm
read -p "Are you sure you want to proceed? Type 'RESET' to confirm: " confirm
if [ "$confirm" != "RESET" ]; then
    echo "❌ Reset cancelled"
    exit 1
fi

echo ""
echo "📦 Step 1: Backing up Keycloak data..."
"$SCRIPT_DIR/backup-keycloak-realms.sh" || {
    echo "⚠️  Backup failed, but continuing with reset..."
}

echo ""
echo "🛑 Step 2: Stopping Keycloak..."
cd "$PROJECT_ROOT"
docker-compose -f docker-compose.dev.yml stop keycloak

echo ""
echo "🗑️  Step 3: Removing Keycloak database volume..."
docker-compose -f docker-compose.dev.yml rm -f keycloak_db 2>/dev/null || true
docker volume rm sentinelgrid-keycloak_db_data 2>/dev/null || {
    echo "⚠️  Volume removal failed (may not exist), continuing..."
}

echo ""
echo "🔄 Step 4: Starting fresh Keycloak database..."
# Ensure KEYCLOAK_ADMIN_PASSWORD is set to 'admin' for dev
export KEYCLOAK_ADMIN_PASSWORD=admin
docker-compose -f docker-compose.dev.yml up -d keycloak_db

echo ""
echo "⏳ Step 5: Waiting for database to be ready..."
sleep 5

echo ""
echo "🚀 Step 6: Starting Keycloak with default admin/admin..."
docker-compose -f docker-compose.dev.yml up -d keycloak

echo ""
echo "⏳ Step 7: Waiting for Keycloak to start (30 seconds)..."
sleep 30

echo ""
echo "🔐 Step 8: Verifying admin credentials..."
if docker-compose -f docker-compose.dev.yml exec -T keycloak \
    /opt/keycloak/bin/kcadm.sh config credentials \
    --server http://localhost:8080 \
    --realm master \
    --user admin \
    --password admin \
    > /dev/null 2>&1; then
    echo "✅ Keycloak reset successful!"
    echo ""
    echo "Login credentials:"
    echo "  Username: admin"
    echo "  Password: admin"
    echo "  Realm: master"
    echo "  Admin Console: http://localhost:8080/admin"
    echo ""
    echo "Next steps:"
    echo "  1. Run seed scripts to recreate realms and users"
    echo "  2. Run: ./scripts/run-seed-demo.sh"
else
    echo "⚠️  Keycloak started but authentication test failed"
    echo "   Try accessing: http://localhost:8080/admin"
    echo "   Or wait a bit longer and check logs"
fi

