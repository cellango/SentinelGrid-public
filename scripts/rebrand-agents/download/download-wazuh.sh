#!/bin/bash
# Download Wazuh Agent packages for rebranding
# This script downloads official Wazuh agent packages for all supported platforms

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="${SCRIPT_DIR}/../../../agents/wazuh"
WAZUH_VERSION="${WAZUH_VERSION:-4.8.0}"
WAZUH_BASE_URL="https://packages.wazuh.com/4.x"

echo "=========================================="
echo "Downloading Wazuh Agent ${WAZUH_VERSION}"
echo "=========================================="
echo ""

# Create agents directory
mkdir -p "${AGENTS_DIR}"

# Function to download file with retry
download_with_retry() {
    local url=$1
    local output=$2
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo "Downloading: $(basename $output) (attempt $attempt/$max_attempts)..."
        # Use curl if wget is not available
        if command -v wget &> /dev/null; then
            if wget -q --show-progress -O "$output" "$url" 2>&1; then
                echo "✅ Downloaded: $(basename $output)"
                return 0
            fi
        elif command -v curl &> /dev/null; then
            if curl -L -# -o "$output" "$url" 2>&1; then
                echo "✅ Downloaded: $(basename $output)"
                return 0
            fi
        else
            echo "❌ Neither wget nor curl found. Please install one of them."
            return 1
        fi
        
        echo "❌ Failed to download: $(basename $output)"
        if [ $attempt -lt $max_attempts ]; then
            echo "Retrying in 5 seconds..."
            sleep 5
        fi
        attempt=$((attempt + 1))
    done
    
    echo "❌ Failed to download after $max_attempts attempts: $(basename $output)"
    return 1
}

# Linux RPM (RHEL/CentOS/Amazon Linux)
echo "📦 Linux RPM (RHEL/CentOS/Amazon Linux)..."
RPM_URL="${WAZUH_BASE_URL}/yum/wazuh-agent-${WAZUH_VERSION}-1.x86_64.rpm"
RPM_FILE="${AGENTS_DIR}/wazuh-agent-${WAZUH_VERSION}-1.x86_64.rpm"
download_with_retry "$RPM_URL" "$RPM_FILE"

# Linux DEB (Debian/Ubuntu)
echo "📦 Linux DEB (Debian/Ubuntu)..."
DEB_URL="${WAZUH_BASE_URL}/apt/pool/main/w/wazuh-agent/wazuh-agent_${WAZUH_VERSION}-1_amd64.deb"
DEB_FILE="${AGENTS_DIR}/wazuh-agent_${WAZUH_VERSION}-1_amd64.deb"
download_with_retry "$DEB_URL" "$DEB_FILE"

# Windows MSI
echo "📦 Windows MSI..."
MSI_URL="${WAZUH_BASE_URL}/windows/wazuh-agent-${WAZUH_VERSION}-1.msi"
MSI_FILE="${AGENTS_DIR}/wazuh-agent-${WAZUH_VERSION}-1.msi"
download_with_retry "$MSI_URL" "$MSI_FILE"

# macOS PKG (Intel)
echo "📦 macOS PKG (Intel)..."
PKG_INTEL_URL="${WAZUH_BASE_URL}/macos/wazuh-agent-${WAZUH_VERSION}-1.intel64.pkg"
PKG_INTEL_FILE="${AGENTS_DIR}/wazuh-agent-${WAZUH_VERSION}-1.intel64.pkg"
download_with_retry "$PKG_INTEL_URL" "$PKG_INTEL_FILE"

# macOS PKG (ARM64)
echo "📦 macOS PKG (ARM64)..."
PKG_ARM_URL="${WAZUH_BASE_URL}/macos/wazuh-agent-${WAZUH_VERSION}-1.arm64.pkg"
PKG_ARM_FILE="${AGENTS_DIR}/wazuh-agent-${WAZUH_VERSION}-1.arm64.pkg"
download_with_retry "$PKG_ARM_URL" "$PKG_ARM_FILE"

# Generate checksums
echo ""
echo "=========================================="
echo "Generating checksums..."
echo "=========================================="

for file in "${AGENTS_DIR}"/*.rpm "${AGENTS_DIR}"/*.deb "${AGENTS_DIR}"/*.msi "${AGENTS_DIR}"/*.pkg; do
    if [ -f "$file" ]; then
        # Use shasum on macOS, sha256sum on Linux
        if command -v sha256sum &> /dev/null; then
            sha256sum "$file" > "${file}.sha256"
        elif command -v shasum &> /dev/null; then
            shasum -a 256 "$file" > "${file}.sha256"
        else
            echo "⚠️  No checksum tool found (sha256sum or shasum)"
            continue
        fi
        echo "✅ Checksum: $(basename $file).sha256"
    fi
done

echo ""
echo "=========================================="
echo "✅ Download complete!"
echo "=========================================="
echo "Downloaded files:"
ls -lh "${AGENTS_DIR}"/*.{rpm,deb,msi,pkg} 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo "Next step: Run rebrand-wazuh.sh to rebrand the agents"

