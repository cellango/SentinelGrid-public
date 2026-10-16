#!/bin/bash
# Keycloak Backup Script
# Exports Keycloak realms and configurations

set -euo pipefail

# Configuration
KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
KEYCLOAK_ADMIN_REALM="${KEYCLOAK_ADMIN_REALM:-master}"
KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT="${KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT:-false}"
KEYCLOAK_ADMIN_USER="${KEYCLOAK_ADMIN_USER:-admin}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-}"
KEYCLOAK_ADMIN_CLIENT_ID="${KEYCLOAK_ADMIN_CLIENT_ID:-admin-cli}"
KEYCLOAK_ADMIN_CLIENT_SECRET="${KEYCLOAK_ADMIN_CLIENT_SECRET:-}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/sentinelgrid/keycloak}"
S3_BUCKET="${S3_BACKUP_BUCKET:-}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FOLDER="${BACKUP_DIR}/keycloak_${TIMESTAMP}"
mkdir -p "$BACKUP_FOLDER"

echo "Starting Keycloak backup..."
echo "Keycloak URL: ${KEYCLOAK_URL}"
echo "Backup folder: keycloak_${TIMESTAMP}"

get_admin_token() {
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

# Get admin access token
echo "Authenticating with Keycloak..."
TOKEN=$(get_admin_token)

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo "✗ Failed to authenticate with Keycloak"
    exit 1
fi

echo "✓ Authentication successful"

# Get list of realms
echo "Fetching realms..."
REALMS=$(curl -fsS -X GET "${KEYCLOAK_URL}/admin/realms" \
    -H "Authorization: Bearer ${TOKEN}" \
    | jq -r '.[].realm')

if [ -z "$REALMS" ]; then
    echo "✗ No realms found"
    exit 1
fi

echo "Found realms: $(echo $REALMS | tr '\n' ', ')"

# Export each realm
for REALM in $REALMS; do
    echo "Exporting realm: ${REALM}..."
    
    # Export realm configuration
    curl -fsS -X GET "${KEYCLOAK_URL}/admin/realms/${REALM}" \
        -H "Authorization: Bearer ${TOKEN}" \
        > "${BACKUP_FOLDER}/realm_${REALM}.json"
    
    # Export realm users (partial export - metadata only, not passwords)
    curl -fsS -X GET "${KEYCLOAK_URL}/admin/realms/${REALM}/users?briefRepresentation=false" \
        -H "Authorization: Bearer ${TOKEN}" \
        > "${BACKUP_FOLDER}/users_${REALM}.json"
    
    # Export realm clients
    curl -fsS -X GET "${KEYCLOAK_URL}/admin/realms/${REALM}/clients" \
        -H "Authorization: Bearer ${TOKEN}" \
        > "${BACKUP_FOLDER}/clients_${REALM}.json"
    
    # Export realm roles
    curl -fsS -X GET "${KEYCLOAK_URL}/admin/realms/${REALM}/roles" \
        -H "Authorization: Bearer ${TOKEN}" \
        > "${BACKUP_FOLDER}/roles_${REALM}.json"
    
    # Export realm groups
    curl -fsS -X GET "${KEYCLOAK_URL}/admin/realms/${REALM}/groups" \
        -H "Authorization: Bearer ${TOKEN}" \
        > "${BACKUP_FOLDER}/groups_${REALM}.json"
    
    echo "✓ Realm ${REALM} exported successfully"
done

# Create metadata file
cat > "${BACKUP_FOLDER}/backup_metadata.json" <<EOF
{
    "backup_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "keycloak_version": "$(curl -fsS ${KEYCLOAK_URL}/realms/master | jq -r '.version' || echo 'unknown')",
    "realms": $(echo "$REALMS" | jq -R -s -c 'split("\n") | map(select(length > 0))'),
    "backup_type": "full"
}
EOF

# Compress backup
echo "Compressing backup..."
cd "$BACKUP_DIR"
tar -czf "keycloak_${TIMESTAMP}.tar.gz" "keycloak_${TIMESTAMP}"
rm -rf "keycloak_${TIMESTAMP}"

BACKUP_FILE="keycloak_${TIMESTAMP}.tar.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

echo "✓ Backup compressed successfully"
BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
echo "  Backup size: ${BACKUP_SIZE}"

# Upload to S3 if configured
if [ -n "$S3_BUCKET" ]; then
    echo "Uploading backup to S3..."
    aws s3 cp "$BACKUP_PATH" "s3://${S3_BUCKET}/keycloak/${BACKUP_FILE}" \
        --storage-class STANDARD_IA \
        --server-side-encryption AES256
    
    if [ $? -eq 0 ]; then
        echo "✓ Backup uploaded to S3: s3://${S3_BUCKET}/keycloak/${BACKUP_FILE}"
    else
        echo "✗ Failed to upload backup to S3"
        exit 1
    fi
fi

# Clean up old backups
echo "Cleaning up old backups (keeping last ${RETENTION_DAYS} days)..."
find "$BACKUP_DIR" -name "keycloak_*.tar.gz" -type f -mtime +${RETENTION_DAYS} -delete

echo ""
echo "Keycloak backup completed successfully at $(date)"
