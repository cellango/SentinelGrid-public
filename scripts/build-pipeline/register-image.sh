#!/bin/bash
# Register built image in database
# This script registers a hardened image in the database with scan results

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
CLOUD_PROVIDER="${1:-}"
IMAGE_ID="${2:-}"
OS_TYPE="${3:-}"
OS_VERSION="${4:-}"
AGENT_VERSION="${5:-1.0.0}"
HARDENING_LEVEL="${6:-cis-level1}"
SCAN_RESULT_FILE="${7:-}"

if [ -z "$CLOUD_PROVIDER" ] || [ -z "$IMAGE_ID" ] || [ -z "$OS_TYPE" ]; then
    echo "Usage: $0 <cloud_provider> <image_id> <os_type> [os_version] [agent_version] [hardening_level] [scan_result_file]"
    echo "  cloud_provider: aws, azure, gcp"
    echo "  image_id: AMI ID, Azure Image ID, or GCP Image ID"
    echo "  os_type: amazon-linux-2, ubuntu-22.04, etc."
    echo "  os_version: 2023, 22.04, etc. (default: extracted from os_type)"
    echo "  agent_version: Agent version (default: 1.0.0)"
    echo "  hardening_level: cis-level1, cis-level2 (default: cis-level1)"
    echo "  scan_result_file: Path to scan results JSON (optional)"
    exit 1
fi

# Extract OS version from OS type if not provided
if [ -z "$OS_VERSION" ]; then
    case $OS_TYPE in
        amazon-linux-2) OS_VERSION="2" ;;
        ubuntu-22.04) OS_VERSION="22.04" ;;
        rhel-8) OS_VERSION="8" ;;
        debian-12) OS_VERSION="12" ;;
        windows-server-2022) OS_VERSION="2022" ;;
        *) OS_VERSION="unknown" ;;
    esac
fi

# Get region
REGION="${AWS_REGION:-us-east-1}"
if [ "$CLOUD_PROVIDER" = "azure" ]; then
    REGION="${AZURE_LOCATION:-East US}"
elif [ "$CLOUD_PROVIDER" = "gcp" ]; then
    REGION="${GCP_ZONE:-us-east1-b}"
fi

# Generate version
VERSION="${OS_TYPE}-${OS_VERSION}-${HARDENING_LEVEL}-agent-${AGENT_VERSION}-$(date +%Y%m%d%H%M%S)"

echo "=========================================="
echo "Registering Hardened Image"
echo "=========================================="
echo "Version: ${VERSION}"
echo "OS Type: ${OS_TYPE}"
echo "OS Version: ${OS_VERSION}"
echo "Cloud Provider: ${CLOUD_PROVIDER}"
echo "Image ID: ${IMAGE_ID}"
echo "Region: ${REGION}"
echo ""

# Parse scan results if provided
SCAN_STATUS="pending"
SCAN_DATE=""
VULN_COUNTS='{"critical": 0, "high": 0, "medium": 0, "low": 0}'

if [ -n "$SCAN_RESULT_FILE" ] && [ -f "$SCAN_RESULT_FILE" ]; then
    if command -v jq &> /dev/null; then
        SCAN_STATUS=$(jq -r '.scan_status // "pending"' "$SCAN_RESULT_FILE")
        SCAN_DATE=$(jq -r '.scan_date // ""' "$SCAN_RESULT_FILE")
        VULN_COUNTS=$(jq -c '.vulnerability_count // {"critical": 0, "high": 0, "medium": 0, "low": 0}' "$SCAN_RESULT_FILE")
    else
        echo "⚠️  jq not available, using default scan status"
    fi
fi

# Check if database is accessible
if [ -z "$DB_URL" ]; then
    echo "⚠️  DB_URL not set, cannot register in database"
    echo "   Image information:"
    echo "   Version: ${VERSION}"
    echo "   Image ID: ${IMAGE_ID}"
    echo "   Scan Status: ${SCAN_STATUS}"
    exit 0
fi

# Register in database using psql or Python script
# For now, output SQL that can be run manually
SQL_FILE="/tmp/register-image-${IMAGE_ID}.sql"

cat > "$SQL_FILE" <<EOF
-- Register hardened image
INSERT INTO hardened_images (
    version, os_type, os_version, cloud_provider, image_id, region,
    agent_version, hardening_level, build_date, status, scan_status,
    scan_date, vulnerability_count, is_latest
) VALUES (
    '${VERSION}',
    '${OS_TYPE}',
    '${OS_VERSION}',
    '${CLOUD_PROVIDER}',
    '${IMAGE_ID}',
    '${REGION}',
    '${AGENT_VERSION}',
    '${HARDENING_LEVEL}',
    NOW(),
    CASE WHEN '${SCAN_STATUS}' = 'passed' THEN 'ready' ELSE 'building' END,
    '${SCAN_STATUS}',
    ${SCAN_DATE:+"'${SCAN_DATE}'"::timestamptz} ${SCAN_DATE:-NULL},
    '${VULN_COUNTS}'::jsonb,
    false  -- Will be set to true if this is the latest
)
ON CONFLICT (os_type, os_version, cloud_provider, region, version) 
DO UPDATE SET
    image_id = EXCLUDED.image_id,
    scan_status = EXCLUDED.scan_status,
    scan_date = EXCLUDED.scan_date,
    vulnerability_count = EXCLUDED.vulnerability_count,
    updated_at = NOW();

-- Update is_latest flag (only one latest per OS+cloud combo)
UPDATE hardened_images
SET is_latest = false
WHERE os_type = '${OS_TYPE}'
  AND os_version = '${OS_VERSION}'
  AND cloud_provider = '${CLOUD_PROVIDER}'
  AND version != '${VERSION}';

UPDATE hardened_images
SET is_latest = true
WHERE version = '${VERSION}';
EOF

echo "SQL script generated: ${SQL_FILE}"
echo ""
echo "To register in database, run:"
echo "  psql \$DB_URL -f ${SQL_FILE}"
echo ""
echo "Or use the API endpoint:"
echo "  POST /api/v1/admin/hardened-images/versions"
echo "  Body: $(cat <<EOJSON
{
  "version": "${VERSION}",
  "os_type": "${OS_TYPE}",
  "os_version": "${OS_VERSION}",
  "cloud_provider": "${CLOUD_PROVIDER}",
  "image_id": "${IMAGE_ID}",
  "region": "${REGION}",
  "agent_version": "${AGENT_VERSION}",
  "hardening_level": "${HARDENING_LEVEL}",
  "scan_status": "${SCAN_STATUS}",
  "vulnerability_count": ${VULN_COUNTS}
}
EOJSON
)"

echo ""
echo "=========================================="
echo "✅ Image registration prepared"
echo "=========================================="

