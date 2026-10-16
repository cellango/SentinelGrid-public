#!/bin/bash
# System Restore Script
# Restores PostgreSQL database and Keycloak configuration from backups

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/var/backups/sentinelgrid}"
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-sentinelgrid}"
POSTGRES_DB="${POSTGRES_DB:-sentinelgrid}"
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
KEYCLOAK_ADMIN_REALM="${KEYCLOAK_ADMIN_REALM:-master}"
KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT="${KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT:-false}"
KEYCLOAK_ADMIN_USER="${KEYCLOAK_ADMIN_USER:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-}"
KEYCLOAK_ADMIN_CLIENT_ID="${KEYCLOAK_ADMIN_CLIENT_ID:-admin-cli}"
KEYCLOAK_ADMIN_CLIENT_SECRET="${KEYCLOAK_ADMIN_CLIENT_SECRET:-}"
S3_BUCKET="${S3_BACKUP_BUCKET:-}"
RESTORE_AUTO_CONFIRM="${RESTORE_AUTO_CONFIRM:-false}"

# Parse command line arguments
RESTORE_COMPONENT="${1}"  # postgres, keycloak, or all
BACKUP_FILE="${2}"        # Optional: specific backup file

if [ -z "$RESTORE_COMPONENT" ]; then
    echo "Usage: $0 <postgres|keycloak|all> [backup_file]"
    echo ""
    echo "Examples:"
    echo "  $0 postgres                              # Restore latest PostgreSQL backup"
    echo "  $0 keycloak                              # Restore latest Keycloak backup"
    echo "  $0 all                                    # Restore both PostgreSQL and Keycloak"
    echo "  $0 postgres sentinelgrid_db_20251202.sql.gz  # Restore specific backup"
    exit 1
fi

confirm_or_exit() {
    local prompt="$1"

    if [[ "${RESTORE_AUTO_CONFIRM}" == "true" ]]; then
        echo "RESTORE_AUTO_CONFIRM=true, proceeding without interactive confirmation"
        return 0
    fi

    read -p "${prompt}" confirm
    if [ "$confirm" != "yes" ]; then
        echo "Restore cancelled"
        return 1
    fi
}

# Function to restore PostgreSQL
restore_postgres() {
    local backup_file="${1}"
    
    echo "=== PostgreSQL Restore ==="
    
    # Find backup file if not specified
    if [ -z "$backup_file" ]; then
        echo "Finding latest PostgreSQL backup..."
        backup_file=$(ls -t "${BACKUP_DIR}/postgres"/sentinelgrid_db_*.sql.gz 2>/dev/null | head -1)
        
        if [ -z "$backup_file" ]; then
            # Try downloading from S3
            if [ -n "$S3_BUCKET" ]; then
                echo "No local backup found, checking S3..."
                LATEST_S3=$(aws s3 ls "s3://${S3_BUCKET}/postgres/" | sort | tail -1 | awk '{print $4}')
                if [ -n "$LATEST_S3" ]; then
                    echo "Downloading from S3: ${LATEST_S3}"
                    mkdir -p "${BACKUP_DIR}/postgres"
                    aws s3 cp "s3://${S3_BUCKET}/postgres/${LATEST_S3}" "${BACKUP_DIR}/postgres/${LATEST_S3}"
                    backup_file="${BACKUP_DIR}/postgres/${LATEST_S3}"
                fi
            fi
        fi
        
        if [ -z "$backup_file" ]; then
            echo "✗ No PostgreSQL backup found"
            return 1
        fi
    fi
    
    echo "Restoring from: ${backup_file}"
    
    # Confirm restore
    if ! confirm_or_exit "⚠️  This will DROP and recreate the database. Continue? (yes/no): "; then
        return 1
    fi
    
    # Terminate existing connections
    echo "Terminating existing database connections..."
    PGPASSWORD="${POSTGRES_PASSWORD}" psql \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();" \
        >/dev/null 2>&1 || true
    
    # Restore database
    echo "Restoring database..."
    # Host pg_dump may be newer than the target server and emit SET statements
    # unknown to the server major version; strip the known transaction_timeout
    # header while still failing closed on any real SQL restore error.
    gunzip -c "$backup_file" \
        | sed '/^SET transaction_timeout = 0;$/d' \
        | PGPASSWORD="${POSTGRES_PASSWORD}" psql \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -v ON_ERROR_STOP=1 \
        --quiet
    
    if [ $? -eq 0 ]; then
        echo "✓ PostgreSQL restored successfully"
        
        # Verify restore
        echo "Verifying restore..."
        TABLE_COUNT=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql \
            -h "$POSTGRES_HOST" \
            -p "$POSTGRES_PORT" \
            -U "$POSTGRES_USER" \
            -d "$POSTGRES_DB" \
            -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
        echo "  Tables found: ${TABLE_COUNT}"
        
        return 0
    else
        echo "✗ PostgreSQL restore failed"
        return 1
    fi
}

# Function to get Keycloak admin token
get_keycloak_admin_token() {
    if [[ "${KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT}" == "true" ]]; then
        if [[ -z "${KEYCLOAK_ADMIN_CLIENT_SECRET}" ]]; then
            echo "✗ KEYCLOAK_ADMIN_CLIENT_SECRET is required when KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT=true"
            return 1
        fi
        curl -fsS -X POST "${KEYCLOAK_URL}/realms/${KEYCLOAK_ADMIN_REALM}/protocol/openid-connect/token" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -d "grant_type=client_credentials" \
            -d "client_id=${KEYCLOAK_ADMIN_CLIENT_ID}" \
            -d "client_secret=${KEYCLOAK_ADMIN_CLIENT_SECRET}" \
            | jq -r '.access_token'
        return 0
    fi

    curl -fsS -X POST "${KEYCLOAK_URL}/realms/${KEYCLOAK_ADMIN_REALM}/protocol/openid-connect/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=${KEYCLOAK_ADMIN_USER}" \
        -d "password=${KEYCLOAK_ADMIN_PASSWORD}" \
        -d "grant_type=password" \
        -d "client_id=${KEYCLOAK_ADMIN_CLIENT_ID}" \
        | jq -r '.access_token'
}

# Function to restore Keycloak
restore_keycloak() {
    local backup_file="${1}"
    
    echo "=== Keycloak Restore ==="
    
    # Find backup file if not specified
    if [ -z "$backup_file" ]; then
        echo "Finding latest Keycloak backup..."
        backup_file=$(ls -t "${BACKUP_DIR}/keycloak"/keycloak_*.tar.gz 2>/dev/null | head -1)
        
        if [ -z "$backup_file" ]; then
            # Try downloading from S3
            if [ -n "$S3_BUCKET" ]; then
                echo "No local backup found, checking S3..."
                LATEST_S3=$(aws s3 ls "s3://${S3_BUCKET}/keycloak/" | sort | tail -1 | awk '{print $4}')
                if [ -n "$LATEST_S3" ]; then
                    echo "Downloading from S3: ${LATEST_S3}"
                    mkdir -p "${BACKUP_DIR}/keycloak"
                    aws s3 cp "s3://${S3_BUCKET}/keycloak/${LATEST_S3}" "${BACKUP_DIR}/keycloak/${LATEST_S3}"
                    backup_file="${BACKUP_DIR}/keycloak/${LATEST_S3}"
                fi
            fi
        fi
        
        if [ -z "$backup_file" ]; then
            echo "✗ No Keycloak backup found"
            return 1
        fi
    fi
    
    echo "Restoring from: ${backup_file}"
    
    # Confirm restore
    if ! confirm_or_exit "⚠️  This will overwrite Keycloak configuration. Continue? (yes/no): "; then
        return 1
    fi
    
    # Extract backup
    TEMP_DIR=$(mktemp -d)
    echo "Extracting backup to ${TEMP_DIR}..."
    tar -xzf "$backup_file" -C "$TEMP_DIR"
    
    BACKUP_FOLDER=$(ls -t "$TEMP_DIR" | head -1)
    BACKUP_PATH="${TEMP_DIR}/${BACKUP_FOLDER}"
    
    # Get admin token
    echo "Authenticating with Keycloak..."
    TOKEN=$(get_keycloak_admin_token)
    
    if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
        echo "✗ Failed to authenticate with Keycloak"
        rm -rf "$TEMP_DIR"
        return 1
    fi
    
    # Restore realms
    for realm_file in "$BACKUP_PATH"/realm_*.json; do
        if [ -f "$realm_file" ]; then
            REALM_NAME=$(jq -r '.realm' "$realm_file")
            echo "Restoring realm: ${REALM_NAME}..."
            
            # Import realm (this will update if exists, create if not)
            curl -fsS -X POST "${KEYCLOAK_URL}/admin/realms" \
                -H "Authorization: Bearer ${TOKEN}" \
                -H "Content-Type: application/json" \
                -d @"$realm_file" \
                >/dev/null 2>&1 || \
            curl -fsS -X PUT "${KEYCLOAK_URL}/admin/realms/${REALM_NAME}" \
                -H "Authorization: Bearer ${TOKEN}" \
                -H "Content-Type: application/json" \
                -d @"$realm_file" \
                >/dev/null
            
            echo "✓ Realm ${REALM_NAME} restored"
        fi
    done
    
    # Clean up
    rm -rf "$TEMP_DIR"
    
    echo "✓ Keycloak restored successfully"
    return 0
}

# Main restore logic
case "$RESTORE_COMPONENT" in
    postgres)
        restore_postgres "$BACKUP_FILE"
        ;;
    keycloak)
        restore_keycloak "$BACKUP_FILE"
        ;;
    all)
        restore_postgres
        POSTGRES_STATUS=$?
        restore_keycloak
        KEYCLOAK_STATUS=$?
        
        if [ $POSTGRES_STATUS -eq 0 ] && [ $KEYCLOAK_STATUS -eq 0 ]; then
            echo ""
            echo "✓ Full system restore completed successfully"
            exit 0
        else
            echo ""
            echo "✗ Some components failed to restore"
            exit 1
        fi
        ;;
    *)
        echo "Invalid component: ${RESTORE_COMPONENT}"
        echo "Use: postgres, keycloak, or all"
        exit 1
        ;;
esac

echo ""
echo "Restore completed at $(date)"
