#!/bin/bash
# Mark version as released and update is_latest flags
# This script marks a version as released and updates latest flags

set -e

TYPE="${1:-}"  # agent or image
VERSION="${2:-}"

if [ -z "$TYPE" ] || [ -z "$VERSION" ]; then
    echo "Usage: $0 <type> <version>"
    echo "  type: agent or image"
    echo "  version: Version to release (e.g., 1.2.3)"
    exit 1
fi

echo "=========================================="
echo "Releasing ${TYPE} Version"
echo "=========================================="
echo "Version: ${VERSION}"
echo ""

if [ -z "$DB_URL" ]; then
    echo "❌ DB_URL not set, cannot update database"
    exit 1
fi

if [ "$TYPE" = "agent" ]; then
    # Update agent version
    psql "$DB_URL" <<EOF
-- Set all versions of this agent type to not latest
UPDATE agent_versions 
SET is_latest = false, updated_at = NOW()
WHERE agent_type = (
    SELECT agent_type FROM agent_versions WHERE version = '${VERSION}' LIMIT 1
);

-- Set this version as latest
UPDATE agent_versions
SET is_latest = true, status = 'stable', updated_at = NOW()
WHERE version = '${VERSION}';
EOF
    
    echo "✅ Agent version ${VERSION} marked as released and latest"
    
elif [ "$TYPE" = "image" ]; then
    # Update image version
    # Get OS and cloud info from version or parameters
    OS_TYPE="${3:-}"
    CLOUD_PROVIDER="${4:-}"
    
    if [ -z "$OS_TYPE" ] || [ -z "$CLOUD_PROVIDER" ]; then
        echo "⚠️  OS type and cloud provider required for images"
        echo "   Usage: $0 image <version> <os_type> <cloud_provider>"
        exit 1
    fi
    
    psql "$DB_URL" <<EOF
-- Set all versions of this OS+cloud combo to not latest
UPDATE hardened_images
SET is_latest = false, updated_at = NOW()
WHERE os_type = '${OS_TYPE}' 
  AND cloud_provider = '${CLOUD_PROVIDER}';

-- Set this version as latest
UPDATE hardened_images
SET is_latest = true, status = 'ready', updated_at = NOW()
WHERE version = '${VERSION}';
EOF
    
    echo "✅ Image version ${VERSION} marked as released and latest"
else
    echo "❌ Invalid type. Must be: agent or image"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Version release complete!"
echo "=========================================="

