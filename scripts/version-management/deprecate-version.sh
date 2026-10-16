#!/bin/bash
# Deprecate old versions and set EOL dates
# This script marks versions as deprecated and sets end-of-life dates

set -e

TYPE="${1:-}"  # agent or image
VERSION="${2:-}"
EOL_DATE="${3:-}"  # YYYY-MM-DD format

if [ -z "$TYPE" ] || [ -z "$VERSION" ]; then
    echo "Usage: $0 <type> <version> [eol_date]"
    echo "  type: agent or image"
    echo "  version: Version to deprecate"
    echo "  eol_date: End-of-life date (YYYY-MM-DD), defaults to 90 days from now"
    exit 1
fi

# Set default EOL date if not provided (90 days from now)
if [ -z "$EOL_DATE" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        EOL_DATE=$(date -v+90d +%Y-%m-%d)
    else
        # Linux
        EOL_DATE=$(date -d "+90 days" +%Y-%m-%d)
    fi
fi

echo "=========================================="
echo "Deprecating ${TYPE} Version"
echo "=========================================="
echo "Version: ${VERSION}"
echo "End of Life: ${EOL_DATE}"
echo ""

if [ -z "$DB_URL" ]; then
    echo "❌ DB_URL not set, cannot update database"
    exit 1
fi

if [ "$TYPE" = "agent" ]; then
    psql "$DB_URL" <<EOF
UPDATE agent_versions
SET status = 'deprecated',
    end_of_life_date = '${EOL_DATE}'::date,
    is_latest = false,
    updated_at = NOW()
WHERE version = '${VERSION}';
EOF
    
    echo "✅ Agent version ${VERSION} deprecated (EOL: ${EOL_DATE})"
    
elif [ "$TYPE" = "image" ]; then
    psql "$DB_URL" <<EOF
UPDATE hardened_images
SET status = 'deprecated',
    is_latest = false,
    updated_at = NOW()
WHERE version = '${VERSION}';
EOF
    
    echo "✅ Image version ${VERSION} deprecated"
else
    echo "❌ Invalid type. Must be: agent or image"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Version deprecation complete!"
echo "=========================================="

