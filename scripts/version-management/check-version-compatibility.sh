#!/bin/bash
# Validate version compatibility
# This script checks if agent and image versions are compatible

set -e

AGENT_VERSION="${1:-}"
IMAGE_VERSION="${2:-}"

if [ -z "$AGENT_VERSION" ] || [ -z "$IMAGE_VERSION" ]; then
    echo "Usage: $0 <agent_version> <image_version>"
    echo "  agent_version: Agent version to check"
    echo "  image_version: Image version to check"
    exit 1
fi

echo "=========================================="
echo "Checking Version Compatibility"
echo "=========================================="
echo "Agent Version: ${AGENT_VERSION}"
echo "Image Version: ${IMAGE_VERSION}"
echo ""

if [ -z "$DB_URL" ]; then
    echo "⚠️  DB_URL not set, cannot check compatibility"
    echo "   Assuming compatible (manual verification required)"
    exit 0
fi

# Check compatibility in database
COMPATIBILITY=$(psql "$DB_URL" -t -c "
    SELECT compatibility_status 
    FROM version_compatibility 
    WHERE agent_version = '${AGENT_VERSION}' 
      AND image_version = '${IMAGE_VERSION}' 
    LIMIT 1" 2>/dev/null | xargs)

if [ -z "$COMPATIBILITY" ]; then
    echo "⚠️  Compatibility status: untested"
    echo "   This combination has not been tested"
    echo ""
    echo "   To mark as compatible:"
    echo "   INSERT INTO version_compatibility (agent_version, image_version, compatibility_status, tested_date)"
    echo "   VALUES ('${AGENT_VERSION}', '${IMAGE_VERSION}', 'compatible', NOW());"
    exit 0
fi

echo "Compatibility Status: ${COMPATIBILITY}"

if [ "$COMPATIBILITY" = "compatible" ]; then
    echo "✅ Versions are compatible"
    exit 0
elif [ "$COMPATIBILITY" = "incompatible" ]; then
    echo "❌ Versions are incompatible"
    exit 1
else
    echo "⚠️  Compatibility status: ${COMPATIBILITY}"
    exit 0
fi

