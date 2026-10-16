#!/bin/bash
# Backup Keycloak realms before reset
# This exports all realm configurations so they can be re-imported

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="$PROJECT_ROOT/backups/keycloak-$(date +%Y%m%d-%H%M%S)"

echo "=" * 60
echo "Backing up Keycloak Realms"
echo "=" * 60
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"
echo "📁 Backup directory: $BACKUP_DIR"
echo ""

# Check if Keycloak is accessible
if ! docker ps --format "{{.Names}}" | grep -q "^sentinelgrid-keycloak-1$"; then
    echo "❌ Keycloak container not running"
    exit 1
fi

# Try to authenticate (may fail if password is wrong, but we'll try)
echo "🔐 Attempting to authenticate..."
if docker exec sentinelgrid-keycloak-1 /opt/keycloak/bin/kcadm.sh config credentials \
    --server http://localhost:8080 \
    --realm master \
    --user admin \
    --password admin \
    > /dev/null 2>&1; then
    echo "✅ Authenticated successfully"
    AUTHENTICATED=true
else
    echo "⚠️  Could not authenticate - will backup database instead"
    AUTHENTICATED=false
fi

if [ "$AUTHENTICATED" = true ]; then
    # Export all realms
    echo ""
    echo "📤 Exporting realms..."
    
    REALMS=$(docker exec sentinelgrid-keycloak-1 /opt/keycloak/bin/kcadm.sh get realms --format csv --fields realm 2>/dev/null | tail -n +2)
    
    for realm in $REALMS; do
        if [ -n "$realm" ]; then
            echo "  Exporting realm: $realm"
            docker exec sentinelgrid-keycloak-1 /opt/keycloak/bin/kcadm.sh \
                get realms/"$realm" -r master \
                > "$BACKUP_DIR/realm-$realm.json" 2>/dev/null || echo "    ⚠️  Failed to export $realm"
        fi
    done
    
    echo "✅ Realm exports completed"
else
    # Backup database instead
    echo ""
    echo "📤 Backing up Keycloak database..."
    docker exec sentinelgrid-keycloak_db-1 pg_dump -U keycloak keycloak \
        > "$BACKUP_DIR/keycloak-database.sql" 2>/dev/null || {
        echo "❌ Failed to backup database"
        exit 1
    }
    echo "✅ Database backup completed"
fi

echo ""
echo "=" * 60
echo "✅ Backup completed!"
echo "=" * 60
echo ""
echo "Backup location: $BACKUP_DIR"
echo ""
echo "To restore:"
if [ "$AUTHENTICATED" = true ]; then
    echo "  Use Keycloak import or kcadm.sh to import realm JSON files"
else
    echo "  Restore database: docker exec -i sentinelgrid-keycloak_db-1 psql -U keycloak keycloak < $BACKUP_DIR/keycloak-database.sql"
fi

