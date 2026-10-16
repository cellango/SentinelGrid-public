#!/bin/bash
# Build and share initial images for new customer
# This script builds hardened images and shares them with customer accounts

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_SCRIPT="${SCRIPT_DIR}/../../scripts/build-pipeline/build-image.sh"
DISTRIBUTE_SCRIPT="${SCRIPT_DIR}/../../scripts/build-pipeline/distribute-images.sh"

TENANT_ID="${1:-}"
TENANT_NAME="${2:-}"

if [ -z "$TENANT_ID" ]; then
    echo "Usage: $0 <tenant_id> [tenant_name]"
    echo "  tenant_id: UUID of the tenant"
    echo "  tenant_name: Optional tenant name"
    exit 1
fi

echo "=========================================="
echo "Provisioning Customer Images"
echo "=========================================="
echo "Tenant: ${TENANT_NAME:-${TENANT_ID}}"
echo ""

# Get customer cloud accounts from database
if [ -z "$DB_URL" ]; then
    echo "❌ DB_URL not set, cannot query customer accounts"
    exit 1
fi

# Get list of cloud providers for this tenant
CLOUD_PROVIDERS=$(psql "$DB_URL" -t -c "SELECT DISTINCT cloud_provider FROM customer_cloud_accounts WHERE tenant_id = '${TENANT_ID}' AND status = 'active'" 2>/dev/null | xargs)

if [ -z "$CLOUD_PROVIDERS" ]; then
    echo "⚠️  No active cloud accounts found for tenant ${TENANT_ID}"
    echo "   Run onboard-customer-images.sh first"
    exit 0
fi

echo "Found cloud providers: ${CLOUD_PROVIDERS}"
echo ""

# Default OS types to build
OS_TYPES=("amazon-linux-2" "ubuntu-22.04")
AGENT_VERSION="${AGENT_VERSION:-1.0.0}"

# Build images for each cloud provider
for CLOUD in $CLOUD_PROVIDERS; do
    echo "Processing cloud provider: ${CLOUD}"
    
    for OS_TYPE in "${OS_TYPES[@]}"; do
        echo ""
        echo "Building ${OS_TYPE} for ${CLOUD}..."
        
        # Build image
        if [ -f "$BUILD_SCRIPT" ]; then
            if "$BUILD_SCRIPT" "$OS_TYPE" "$CLOUD" "$AGENT_VERSION"; then
                echo "✅ Image built successfully"
                
                # Get image ID from Packer manifest (simplified - in production, parse manifest.json)
                echo "⚠️  Note: Image ID should be extracted from Packer manifest"
                echo "   Run scan-image.sh and register-image.sh manually"
            else
                echo "❌ Failed to build image"
            fi
        else
            echo "⚠️  Build script not found: ${BUILD_SCRIPT}"
        fi
    done
done

echo ""
echo "=========================================="
echo "✅ Image provisioning initiated"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Wait for images to finish building"
echo "2. Run scan-image.sh for each image"
echo "3. Run register-image.sh for each image"
echo "4. Run distribute-images.sh to share with customer"

