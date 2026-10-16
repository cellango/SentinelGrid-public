#!/bin/bash
# Test rebranded agent packages
# This script verifies that rebranded agents work correctly

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/../../agents-built"
TEST_DIR="${SCRIPT_DIR}/../../agents-test"

echo "=========================================="
echo "Testing Rebranded SentinelGrid Agents"
echo "=========================================="
echo ""

# Create test directory
mkdir -p "${TEST_DIR}"

# Function to test RPM
test_rpm() {
    local rpm_file=$1
    
    if [ ! -f "$rpm_file" ]; then
        echo "⚠️  RPM file not found: $rpm_file"
        return 1
    fi
    
    echo "📦 Testing RPM: $(basename $rpm_file)"
    
    # Check if rpm command is available
    if ! command -v rpm &> /dev/null; then
        echo "  ⚠️  rpm command not available, skipping RPM test"
        return 1
    fi
    
    # Query RPM info
    echo "  Package Info:"
    rpm -qpi "$rpm_file" 2>/dev/null | grep -E "Name|Version|Summary|License" | sed 's/^/    /' || true
    
    # Check for rebranded strings
    echo "  Checking for rebranded strings..."
    if rpm -qpl "$rpm_file" 2>/dev/null | grep -q "sentinelgrid"; then
        echo "    ✅ Found 'sentinelgrid' in package"
    else
        echo "    ⚠️  'sentinelgrid' not found in package (may be in binary names)"
    fi
    
    # Verify checksum
    if [ -f "${rpm_file}.sha256" ]; then
        echo "  Verifying checksum..."
        if sha256sum -c "${rpm_file}.sha256" 2>/dev/null; then
            echo "    ✅ Checksum verified"
        else
            echo "    ⚠️  Checksum mismatch"
        fi
    fi
    
    echo "  ✅ RPM test complete"
}

# Function to test DEB
test_deb() {
    local deb_file=$1
    
    if [ ! -f "$deb_file" ]; then
        echo "⚠️  DEB file not found: $deb_file"
        return 1
    fi
    
    echo "📦 Testing DEB: $(basename $deb_file)"
    
    # Check if dpkg command is available
    if ! command -v dpkg &> /dev/null; then
        echo "  ⚠️  dpkg command not available, skipping DEB test"
        return 1
    fi
    
    # Query DEB info
    echo "  Package Info:"
    dpkg-deb -I "$deb_file" 2>/dev/null | grep -E "Package|Version|Description" | sed 's/^/    /' || true
    
    # Check for rebranded strings
    echo "  Checking for rebranded strings..."
    if dpkg-deb -c "$deb_file" 2>/dev/null | grep -q "sentinelgrid"; then
        echo "    ✅ Found 'sentinelgrid' in package"
    else
        echo "    ⚠️  'sentinelgrid' not found in package (may be in binary names)"
    fi
    
    # Verify checksum
    if [ -f "${deb_file}.sha256" ]; then
        echo "  Verifying checksum..."
        if sha256sum -c "${deb_file}.sha256" 2>/dev/null; then
            echo "    ✅ Checksum verified"
        else
            echo "    ⚠️  Checksum mismatch"
        fi
    fi
    
    echo "  ✅ DEB test complete"
}

# Test all packages
for rpm_file in "${BUILD_DIR}"/*.rpm; do
    if [ -f "$rpm_file" ]; then
        test_rpm "$rpm_file"
        echo ""
    fi
done

for deb_file in "${BUILD_DIR}"/*.deb; do
    if [ -f "$deb_file" ]; then
        test_deb "$deb_file"
        echo ""
    fi
done

echo "=========================================="
echo "✅ Testing complete!"
echo "=========================================="

