#!/bin/bash
# Reset Keycloak admin password to default 'admin' for dev environment

set -e

echo "🔄 Resetting Keycloak admin password to 'admin'..."
echo ""

CONTAINER="sentinelgrid-keycloak-1"
DB_CONTAINER="sentinelgrid-keycloak_db-1"

# Check if containers are running
if ! docker ps --format "{{.Names}}" | grep -q "^${CONTAINER}$"; then
    echo "❌ Keycloak container not found: $CONTAINER"
    exit 1
fi

if ! docker ps --format "{{.Names}}" | grep -q "^${DB_CONTAINER}$"; then
    echo "❌ Keycloak database container not found: $DB_CONTAINER"
    exit 1
fi

echo "✅ Containers found"
echo ""

# Method 1: Try using Keycloak's built-in admin user creation
# This works if we delete the admin user and let Keycloak recreate it
echo "🔧 Attempting to reset admin password..."
echo ""

# Get admin user ID
ADMIN_USER_ID=$(docker exec $DB_CONTAINER psql -U keycloak -d keycloak -t -c "
SELECT id FROM user_entity 
WHERE username = 'admin' 
AND realm_id = (SELECT id FROM realm WHERE name = 'master')
LIMIT 1;
" 2>/dev/null | xargs)

if [ -z "$ADMIN_USER_ID" ]; then
    echo "❌ Admin user not found in master realm"
    exit 1
fi

echo "✅ Found admin user: $ADMIN_USER_ID"
echo ""

# Delete all credentials for admin user
echo "🗑️  Deleting existing credentials..."
docker exec $DB_CONTAINER psql -U keycloak -d keycloak -c "
DELETE FROM credential 
WHERE user_id = '$ADMIN_USER_ID';
" > /dev/null 2>&1

echo "✅ Credentials deleted"
echo ""

# Restart Keycloak with KEYCLOAK_ADMIN_PASSWORD=admin
echo "🔄 Restarting Keycloak with KEYCLOAK_ADMIN_PASSWORD=admin..."
cd "$(dirname "$0")/.."
KEYCLOAK_ADMIN_PASSWORD=admin docker-compose -f docker-compose.dev.yml restart keycloak > /dev/null 2>&1

echo "⏳ Waiting for Keycloak to start..."
sleep 20

# Test authentication
echo "🔐 Testing authentication..."
if docker exec $CONTAINER /opt/keycloak/bin/kcadm.sh config credentials \
    --server http://localhost:8080 \
    --realm master \
    --user admin \
    --password admin \
    > /dev/null 2>&1; then
    echo "✅ Admin password reset successful!"
    echo ""
    echo "Login credentials:"
    echo "  Username: admin"
    echo "  Password: admin"
    echo "  Realm: master"
    exit 0
else
    echo "⚠️  Authentication test failed"
    echo ""
    echo "The credential was deleted, but Keycloak may need to recreate it."
    echo "Try accessing the Keycloak Admin Console: http://localhost:8080/admin"
    echo "Or wait a bit longer and try again."
    exit 1
fi

