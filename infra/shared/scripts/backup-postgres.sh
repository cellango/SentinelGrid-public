#!/bin/bash
# PostgreSQL Backup Script
# Performs full database backup with compression and S3 upload

set -euo pipefail

# Configuration
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-sentinelgrid}"
POSTGRES_DB="${POSTGRES_DB:-sentinelgrid}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/sentinelgrid/postgres}"
S3_BUCKET="${S3_BACKUP_BUCKET:-}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="sentinelgrid_db_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

echo "Starting PostgreSQL backup..."
echo "Database: ${POSTGRES_DB}"
echo "Backup file: ${BACKUP_FILE}"

# Perform backup with pg_dump (compressed)
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --clean \
    --if-exists \
    --verbose \
    | gzip > "$BACKUP_PATH"

gzip -t "$BACKUP_PATH"

if [[ ! -s "$BACKUP_PATH" ]]; then
    echo "✗ Database backup failed: archive is empty"
    exit 1
fi

echo "✓ Database backup completed successfully"
BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
echo "  Backup size: ${BACKUP_SIZE}"

# Upload to S3 if configured
if [ -n "$S3_BUCKET" ]; then
    echo "Uploading backup to S3..."
    aws s3 cp "$BACKUP_PATH" "s3://${S3_BUCKET}/postgres/${BACKUP_FILE}" \
        --storage-class STANDARD_IA \
        --server-side-encryption AES256
    
    if [ $? -eq 0 ]; then
        echo "✓ Backup uploaded to S3: s3://${S3_BUCKET}/postgres/${BACKUP_FILE}"
    else
        echo "✗ Failed to upload backup to S3"
        exit 1
    fi
fi

# Clean up old local backups (keep last N days)
echo "Cleaning up old backups (keeping last ${RETENTION_DAYS} days)..."
find "$BACKUP_DIR" -name "sentinelgrid_db_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete

# List remaining backups
echo ""
echo "Current local backups:"
ls -lh "$BACKUP_DIR"/sentinelgrid_db_*.sql.gz 2>/dev/null || echo "  No local backups found"

echo ""
echo "Backup completed successfully at $(date)"
