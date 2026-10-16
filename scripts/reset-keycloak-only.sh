#!/bin/bash
# Reset ONLY Keycloak database (preserves SentinelGrid database)
# This resets Keycloak to fresh state with admin/admin credentials

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=" * 70
echo "Reset Keycloak Only (Preserves SentinelGrid Database)"
echo "=" * 70
echo ""
echo "This will:"
echo "  ❌ Delete all Keycloak realms, users, clients"
echo "  ✅ Keep SentinelGrid database (tenants, apps, alerts, etc.)"
echo "  ✅ Recreate Keycloak with default admin/admin credentials"
echo ""

read -p "Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Reset cancelled"
    exit 1
fi

echo ""
echo "🛑 Step 1: Stopping Keycloak..."
cd "$PROJECT_ROOT"
docker-compose -f docker-compose.dev.yml stop keycloak keycloak_db

echo ""
echo "🗑️  Step 2: Removing Keycloak containers and volumes..."
docker-compose -f docker-compose.dev.yml rm -f keycloak keycloak_db 2>/dev/null || true

# Remove Keycloak volumes
KEYCLOAK_VOLS=$(docker volume ls --format '{{.Name}}' | grep -E "(keycloak|sentinelgrid.*keycloak)" || echo "")
if [ -n "$KEYCLOAK_VOLS" ]; then
    echo "$KEYCLOAK_VOLS" | while read vol; do
        echo "  Removing volume: $vol"
        docker volume rm -f "$vol" 2>/dev/null || true
    done
fi

echo ""
echo "🚀 Step 3: Starting fresh Keycloak..."
# Ensure KEYCLOAK_ADMIN_PASSWORD is set to 'admin' for dev
export KEYCLOAK_ADMIN_PASSWORD=admin
docker-compose -f docker-compose.dev.yml up -d keycloak_db keycloak

echo ""
echo "⏳ Step 4: Waiting for Keycloak to start (30 seconds)..."
sleep 30

echo ""
echo "🔐 Step 5: Verifying admin credentials..."
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
    echo "   Or wait a bit longer and check logs: docker-compose -f docker-compose.dev.yml logs keycloak"
fi

