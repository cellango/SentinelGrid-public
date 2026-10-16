#!/bin/bash
# Build hardened image with Packer
# This script wraps Packer build with proper variables and ensures agents are available

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKER_DIR="${SCRIPT_DIR}/../../packer"

# Configuration
OS_TYPE="${1:-}"
CLOUD_PROVIDER="${2:-aws}"
AGENT_VERSION="${3:-1.0.0}"
TENANT_TOKEN="${4:-}"

if [ -z "$OS_TYPE" ]; then
    echo "Usage: $0 <os_type> [cloud_provider] [agent_version] [tenant_token]"
    echo "  os_type: amazon-linux-2, ubuntu-22.04, rhel-8, debian-12, windows-server-2022"
    echo "  cloud_provider: aws, azure, gcp (default: aws)"
    echo "  agent_version: Agent version to install (default: 1.0.0)"
    echo "  tenant_token: Optional tenant token for agent configuration"
    exit 1
fi

echo "=========================================="
echo "Building Hardened Image"
echo "=========================================="
echo "OS Type: ${OS_TYPE}"
echo "Cloud Provider: ${CLOUD_PROVIDER}"
echo "Agent Version: ${AGENT_VERSION}"
echo ""

# Validate OS type
VALID_OS_TYPES=("amazon-linux-2" "ubuntu-22.04" "rhel-8" "debian-12" "windows-server-2022")
if [[ ! " ${VALID_OS_TYPES[@]} " =~ " ${OS_TYPE} " ]]; then
    echo "❌ Invalid OS type: ${OS_TYPE}"
    echo "Valid types: ${VALID_OS_TYPES[*]}"
    exit 1
fi

# Validate cloud provider
VALID_PROVIDERS=("aws" "azure" "gcp")
if [[ ! " ${VALID_PROVIDERS[@]} " =~ " ${CLOUD_PROVIDER} " ]]; then
    echo "❌ Invalid cloud provider: ${CLOUD_PROVIDER}"
    echo "Valid providers: ${VALID_PROVIDERS[*]}"
    exit 1
fi

# Check if Packer is installed
if ! command -v packer &> /dev/null; then
    echo "❌ Packer not found. Please install Packer first."
    exit 1
fi

# Check if agent version exists in CDN
echo "Checking agent availability..."
AGENT_CDN_URL="https://agents.sentinelgrid.ai"
if [ "$OS_TYPE" = "windows-server-2022" ]; then
    AGENT_URL="${AGENT_CDN_URL}/v${AGENT_VERSION}/windows/sentinelgrid-agent-${AGENT_VERSION}-1.msi"
else
    # Check for RPM or DEB based on OS
    if [[ "$OS_TYPE" =~ ^(amazon-linux-2|rhel-8)$ ]]; then
        AGENT_URL="${AGENT_CDN_URL}/v${AGENT_VERSION}/linux/rpm/sentinelgrid-agent-${AGENT_VERSION}-1.x86_64.rpm"
    elif [[ "$OS_TYPE" =~ ^(ubuntu-22.04|debian-12)$ ]]; then
        AGENT_URL="${AGENT_CDN_URL}/v${AGENT_VERSION}/linux/deb/sentinelgrid-agent_${AGENT_VERSION}-1_amd64.deb"
    fi
fi

# Verify agent is available (optional check - don't fail if CDN is not accessible)
if command -v curl &> /dev/null; then
    if curl -s --head --fail "$AGENT_URL" > /dev/null 2>&1; then
        echo "✅ Agent version ${AGENT_VERSION} is available"
    else
        echo "⚠️  Warning: Agent version ${AGENT_VERSION} may not be available at CDN"
        echo "   URL: ${AGENT_URL}"
        echo "   Continuing anyway..."
    fi
fi

# Find Packer template
TEMPLATE_PATH="${PACKER_DIR}/${OS_TYPE}/${CLOUD_PROVIDER}/${OS_TYPE}.json"

if [ ! -f "$TEMPLATE_PATH" ]; then
    echo "❌ Packer template not found: ${TEMPLATE_PATH}"
    exit 1
fi

echo "Using template: ${TEMPLATE_PATH}"

# Build image with Packer
echo ""
echo "Building image with Packer..."
echo "This may take 15-30 minutes..."

cd "$(dirname "$TEMPLATE_PATH")"

# Build Packer command with variables
PACKER_VARS=(
    "-var" "sentinelgrid_agent_version=${AGENT_VERSION}"
)

if [ -n "$TENANT_TOKEN" ]; then
    PACKER_VARS+=("-var" "sentinelgrid_tenant_token=${TENANT_TOKEN}")
fi

# Add cloud provider specific variables if needed
if [ "$CLOUD_PROVIDER" = "aws" ]; then
    # Use default region if not set
    AWS_REGION="${AWS_REGION:-us-east-1}"
    PACKER_VARS+=("-var" "aws_region=${AWS_REGION}")
fi

# Run Packer build
if packer build "${PACKER_VARS[@]}" "$(basename "$TEMPLATE_PATH")"; then
    echo ""
    echo "=========================================="
    echo "✅ Image build complete!"
    echo "=========================================="
    echo ""
    echo "Next steps:"
    echo "1. Run scan-image.sh to scan the image"
    echo "2. Run register-image.sh to register in database"
    echo "3. Run distribute-images.sh to share with customers"
else
    echo ""
    echo "❌ Image build failed"
    exit 1
fi

