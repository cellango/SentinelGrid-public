#!/bin/bash
# Rebrand Wazuh Agent packages to SentinelGrid Endpoint Protection
# This script replaces branding strings and updates package metadata

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="${SCRIPT_DIR}/../../../agents/wazuh"
REBRAND_DIR="${SCRIPT_DIR}/../../../agents-rebranded"
TEMPLATE_DIR="${SCRIPT_DIR}/../templates"
ATTRIBUTION_TEMPLATE="${TEMPLATE_DIR}/SENTINELGRID_ATTRIBUTION.txt.tmpl"
WAZUH_VERSION="${WAZUH_VERSION:-4.8.0}"
SENTINELGRID_VERSION="${SENTINELGRID_VERSION:-1.0.0}"

echo "=========================================="
echo "Rebranding Wazuh Agent to SentinelGrid"
echo "=========================================="
echo "Wazuh Version: ${WAZUH_VERSION}"
echo "SentinelGrid Version: ${SENTINELGRID_VERSION}"
echo ""

# Create rebrand directory
mkdir -p "${REBRAND_DIR}"

# Function to extract and rebrand RPM
rebrand_rpm() {
    local rpm_file=$1
    local base_name=$(basename "$rpm_file" .rpm)
    local extract_dir="${REBRAND_DIR}/rpm-extract"
    local rebuild_dir="${REBRAND_DIR}/rpm-rebuild"
    
    echo "📦 Processing RPM: $(basename $rpm_file)"
    
    # Clean previous extracts
    rm -rf "$extract_dir" "$rebuild_dir"
    mkdir -p "$extract_dir" "$rebuild_dir"
    
    # Extract RPM
    echo "  Extracting RPM..."
    cd "$extract_dir"
    rpm2cpio "$rpm_file" | cpio -idmv 2>/dev/null || {
        echo "  ⚠️  rpm2cpio not available, skipping RPM rebranding"
        echo "  Install rpm2cpio or use a RHEL/CentOS system"
        return 1
    }
    
    # Rebrand files
    echo "  Rebranding files..."
    find . -type f \( -name "*.conf" -o -name "*.xml" -o -name "*.sh" -o -name "*.py" -o -name "*.service" \) -exec sed -i.bak \
        -e 's/Wazuh/SentinelGrid Endpoint Protection/g' \
        -e 's/wazuh-agent/sentinelgrid-agent/g' \
        -e 's/wazuh-manager/sentinelgrid-manager/g' \
        -e 's/manager\.wazuh\.com/manager.sentinelgrid.ai/g' \
        -e 's/wazuh\.com/sentinelgrid.ai/g' \
        {} \;
    
    # Remove backup files
    find . -name "*.bak" -delete
    
    # Update package metadata (if spec file exists)
    if [ -f "*.spec" ]; then
        sed -i.bak \
            -e "s/Name:.*wazuh.*/Name: sentinelgrid-agent/g" \
            -e "s/Summary:.*Wazuh.*/Summary: SentinelGrid Endpoint Protection Agent/g" \
            -e "s/Version:.*/Version: ${SENTINELGRID_VERSION}/g" \
            -e "s/Release:.*/Release: 1/g" \
            *.spec
        rm -f *.spec.bak
    fi
    
    echo "  ✅ RPM rebranded (ready for rebuild)"
}

# Function to extract and rebrand DEB
rebrand_deb() {
    local deb_file=$1
    local base_name=$(basename "$deb_file" .deb)
    local extract_dir="${REBRAND_DIR}/deb-extract"
    
    echo "📦 Processing DEB: $(basename $deb_file)"
    
    # Clean previous extracts
    rm -rf "$extract_dir"
    mkdir -p "$extract_dir"
    
    # Extract DEB
    echo "  Extracting DEB..."
    cd "$extract_dir"
    dpkg-deb -x "$deb_file" . 2>/dev/null || {
        echo "  ⚠️  dpkg-deb not available, skipping DEB rebranding"
        echo "  Install dpkg or use a Debian/Ubuntu system"
        return 1
    }
    
    dpkg-deb -e "$deb_file" DEBIAN 2>/dev/null || true
    
    # Rebrand files
    echo "  Rebranding files..."
    find . -type f \( -name "*.conf" -o -name "*.xml" -o -name "*.sh" -o -name "*.py" -o -name "*.service" \) -exec sed -i.bak \
        -e 's/Wazuh/SentinelGrid Endpoint Protection/g' \
        -e 's/wazuh-agent/sentinelgrid-agent/g' \
        -e 's/wazuh-manager/sentinelgrid-manager/g' \
        -e 's/manager\.wazuh\.com/manager.sentinelgrid.ai/g' \
        -e 's/wazuh\.com/sentinelgrid.ai/g' \
        {} \;
    
    # Remove backup files
    find . -name "*.bak" -delete
    
    # Update DEB control file
    if [ -f "DEBIAN/control" ]; then
        sed -i.bak \
            -e "s/Package:.*wazuh.*/Package: sentinelgrid-agent/g" \
            -e "s/Description:.*Wazuh.*/Description: SentinelGrid Endpoint Protection Agent/g" \
            -e "s/Version:.*/Version: ${SENTINELGRID_VERSION}-1/g" \
            DEBIAN/control
        rm -f DEBIAN/control.bak
    fi
    
    echo "  ✅ DEB rebranded (ready for rebuild)"
}

# Function to add attribution file
add_attribution() {
    local target_dir=$1
    
    echo "  Adding attribution file..."
    if [ ! -f "${ATTRIBUTION_TEMPLATE}" ]; then
        echo "  ❌ Attribution template not found: ${ATTRIBUTION_TEMPLATE}"
        return 1
    fi

    sed \
        -e "s/__SENTINELGRID_VERSION__/${SENTINELGRID_VERSION}/g" \
        -e "s/__WAZUH_VERSION__/${WAZUH_VERSION}/g" \
        "${ATTRIBUTION_TEMPLATE}" > "${target_dir}/SENTINELGRID_ATTRIBUTION.txt"
    echo "  ✅ Attribution file added"
}

# Process each package type
if [ -f "${AGENTS_DIR}/wazuh-agent-${WAZUH_VERSION}-1.x86_64.rpm" ]; then
    rebrand_rpm "${AGENTS_DIR}/wazuh-agent-${WAZUH_VERSION}-1.x86_64.rpm"
    add_attribution "${REBRAND_DIR}/rpm-extract"
fi

if [ -f "${AGENTS_DIR}/wazuh-agent_${WAZUH_VERSION}-1_amd64.deb" ]; then
    rebrand_deb "${AGENTS_DIR}/wazuh-agent_${WAZUH_VERSION}-1_amd64.deb"
    add_attribution "${REBRAND_DIR}/deb-extract"
fi

# Note: MSI and PKG rebranding require specialized tools
# These would need to be done on Windows/macOS respectively
echo ""
echo "⚠️  Note: MSI and PKG rebranding require Windows/macOS tools"
echo "   These packages should be rebranded on their respective platforms"

echo ""
echo "=========================================="
echo "✅ Rebranding complete!"
echo "=========================================="
echo "Rebranded files are in: ${REBRAND_DIR}"
echo ""
echo "Next step: Run build-packages.sh to rebuild packages"
