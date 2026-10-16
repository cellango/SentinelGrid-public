#!/bin/bash
# Extract agent packages for rebranding
# This script extracts RPM, DEB, MSI, and PKG packages

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="${SCRIPT_DIR}/../../agents/wazuh"
EXTRACT_DIR="${SCRIPT_DIR}/../../agents-extracted"
WAZUH_VERSION="${WAZUH_VERSION:-4.8.0}"

echo "=========================================="
echo "Extracting Agent Packages"
echo "=========================================="
echo ""

# Create extract directory
mkdir -p "${EXTRACT_DIR}"

# Function to extract RPM
extract_rpm() {
    local rpm_file=$1
    local extract_path="${EXTRACT_DIR}/rpm/$(basename "$rpm_file" .rpm)"
    
    echo "📦 Extracting RPM: $(basename $rpm_file)"
    
    if ! command -v rpm2cpio &> /dev/null; then
        echo "  ⚠️  rpm2cpio not available, skipping RPM extraction"
        echo "  Install rpm or use a RHEL/CentOS system"
        return 1
    fi
    
    mkdir -p "$extract_path"
    cd "$extract_path"
    
    rpm2cpio "$rpm_file" | cpio -idmv 2>/dev/null || {
        echo "  ❌ Failed to extract RPM"
        return 1
    }
    
    echo "  ✅ Extracted to: $extract_path"
}

# Function to extract DEB
extract_deb() {
    local deb_file=$1
    local extract_path="${EXTRACT_DIR}/deb/$(basename "$deb_file" .deb)"
    
    echo "📦 Extracting DEB: $(basename $deb_file)"
    
    if ! command -v dpkg-deb &> /dev/null; then
        echo "  ⚠️  dpkg-deb not available, skipping DEB extraction"
        echo "  Install dpkg or use a Debian/Ubuntu system"
        return 1
    fi
    
    mkdir -p "$extract_path"
    
    # Extract data
    dpkg-deb -x "$deb_file" "$extract_path" 2>/dev/null || {
        echo "  ❌ Failed to extract DEB data"
        return 1
    }
    
    # Extract control
    mkdir -p "$extract_path/DEBIAN"
    dpkg-deb -e "$deb_file" "$extract_path/DEBIAN" 2>/dev/null || true
    
    echo "  ✅ Extracted to: $extract_path"
}

# Function to extract MSI (requires msiextract or 7z)
extract_msi() {
    local msi_file=$1
    local extract_path="${EXTRACT_DIR}/msi/$(basename "$msi_file" .msi)"
    
    echo "📦 Extracting MSI: $(basename $msi_file)"
    
    mkdir -p "$extract_path"
    
    # Try msiextract (from msitools)
    if command -v msiextract &> /dev/null; then
        cd "$extract_path"
        msiextract "$msi_file" 2>/dev/null || {
            echo "  ❌ Failed to extract MSI with msiextract"
            return 1
        }
        echo "  ✅ Extracted to: $extract_path"
        return 0
    fi
    
    # Try 7z
    if command -v 7z &> /dev/null; then
        cd "$extract_path"
        7z x "$msi_file" 2>/dev/null || {
            echo "  ❌ Failed to extract MSI with 7z"
            return 1
        }
        echo "  ✅ Extracted to: $extract_path"
        return 0
    fi
    
    echo "  ⚠️  No MSI extraction tool available (msiextract or 7z)"
    echo "  Install msitools or p7zip-full"
    return 1
}

# Function to extract PKG (macOS)
extract_pkg() {
    local pkg_file=$1
    local extract_path="${EXTRACT_DIR}/pkg/$(basename "$pkg_file" .pkg)"
    
    echo "📦 Extracting PKG: $(basename $pkg_file)"
    
    if [[ "$(uname)" != "Darwin" ]]; then
        echo "  ⚠️  PKG extraction requires macOS"
        return 1
    fi
    
    mkdir -p "$extract_path"
    
    # Use pkgutil (macOS built-in)
    if command -v pkgutil &> /dev/null; then
        cd "$extract_path"
        pkgutil --expand "$pkg_file" expanded 2>/dev/null || {
            echo "  ❌ Failed to expand PKG"
            return 1
        }
        
        # Extract payload if it's a xar archive
        if [ -f "expanded/Payload" ]; then
            if command -v xar &> /dev/null; then
                xar -xf "expanded/Payload" 2>/dev/null || true
            fi
        fi
        
        echo "  ✅ Extracted to: $extract_path"
        return 0
    fi
    
    echo "  ⚠️  pkgutil not available"
    return 1
}

# Extract all available packages
if [ -f "${AGENTS_DIR}/wazuh-agent-${WAZUH_VERSION}-1.x86_64.rpm" ]; then
    extract_rpm "${AGENTS_DIR}/wazuh-agent-${WAZUH_VERSION}-1.x86_64.rpm" || true
fi

if [ -f "${AGENTS_DIR}/wazuh-agent_${WAZUH_VERSION}-1_amd64.deb" ]; then
    extract_deb "${AGENTS_DIR}/wazuh-agent_${WAZUH_VERSION}-1_amd64.deb" || true
fi

if [ -f "${AGENTS_DIR}/wazuh-agent-${WAZUH_VERSION}-1.msi" ]; then
    extract_msi "${AGENTS_DIR}/wazuh-agent-${WAZUH_VERSION}-1.msi" || true
fi

if [ -f "${AGENTS_DIR}/wazuh-agent-${WAZUH_VERSION}-1.pkg" ]; then
    extract_pkg "${AGENTS_DIR}/wazuh-agent-${WAZUH_VERSION}-1.pkg" || true
fi

echo ""
echo "=========================================="
echo "✅ Extraction complete!"
echo "=========================================="
echo "Extracted files are in: ${EXTRACT_DIR}"
echo ""
echo "Next step: Run rebrand-wazuh.sh to rebrand the extracted agents"

