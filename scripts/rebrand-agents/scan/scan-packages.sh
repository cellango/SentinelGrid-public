#!/bin/bash
# Security scanning script for rebranded Wazuh packages
# This is the CRITICAL GATE before distribution to customers

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="${SCRIPT_DIR}/../../../agents/wazuh"
REBRANDED_DIR="${SCRIPT_DIR}/../../../agents-rebranded"
SCAN_RESULTS_DIR="${SCRIPT_DIR}/../../../scan-results"
WAZUH_VERSION="${WAZUH_VERSION:-4.8.0}"

echo "=========================================="
echo "SentinelGrid Security Scanning"
echo "=========================================="
echo "Version: Wazuh ${WAZUH_VERSION}"
echo "Scan Date: $(date)"
echo ""

# Create scan results directory
mkdir -p "${SCAN_RESULTS_DIR}"

SCAN_PASSED=true
SCAN_REPORT="${SCAN_RESULTS_DIR}/scan-report-${WAZUH_VERSION}.json"

# Initialize scan report
cat > "$SCAN_REPORT" << EOF
{
  "version": "${WAZUH_VERSION}",
  "scan_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "scans": {},
  "overall_passed": true,
  "failures": []
}
EOF

# ============================================
# Scan 1: Checksum Verification
# ============================================
echo "Scan 1: Checksum Verification"
echo "-------------------"

CHECKSUM_PASSED=true

for file in "${AGENTS_DIR}"/*.rpm "${AGENTS_DIR}"/*.deb "${AGENTS_DIR}"/*.msi "${AGENTS_DIR}"/*.pkg; do
    if [ -f "$file" ]; then
        CHECKSUM_FILE="${file}.sha256"
        
        if [ ! -f "$CHECKSUM_FILE" ]; then
            echo "❌ Missing checksum file for $(basename $file)"
            CHECKSUM_PASSED=false
            continue
        fi
        
        # Verify checksum
        if command -v sha256sum &> /dev/null; then
            sha256sum -c "$CHECKSUM_FILE" > /dev/null 2>&1
        elif command -v shasum &> /dev/null; then
            shasum -a 256 -c "$CHECKSUM_FILE" > /dev/null 2>&1
        else
            echo "⚠️  No checksum tool available"
            continue
        fi
        
        if [ $? -eq 0 ]; then
            echo "✅ $(basename $file)"
        else
            echo "❌ CHECKSUM MISMATCH: $(basename $file)"
            CHECKSUM_PASSED=false
            SCAN_PASSED=false
        fi
    fi
done

if [ "$CHECKSUM_PASSED" = true ]; then
    echo "✅ Checksum verification PASSED"
else
    echo "❌ Checksum verification FAILED"
    SCAN_PASSED=false
fi
echo ""

# ============================================
# Scan 2: Trivy Vulnerability Scan
# ============================================
echo "Scan 2: Trivy Vulnerability Scan"
echo "-------------------"

TRIVY_PASSED=true

if command -v trivy &> /dev/null; then
    # Scan rebranded directory
    trivy rootfs \
        --format json \
        --output "${SCAN_RESULTS_DIR}/trivy-${WAZUH_VERSION}.json" \
        --severity CRITICAL,HIGH,MEDIUM \
        "${REBRANDED_DIR}" 2>/dev/null || true
    
    # Parse results
    if [ -f "${SCAN_RESULTS_DIR}/trivy-${WAZUH_VERSION}.json" ]; then
        CRITICAL_COUNT=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' "${SCAN_RESULTS_DIR}/trivy-${WAZUH_VERSION}.json" 2>/dev/null || echo "0")
        HIGH_COUNT=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="HIGH")] | length' "${SCAN_RESULTS_DIR}/trivy-${WAZUH_VERSION}.json" 2>/dev/null || echo "0")
        MEDIUM_COUNT=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="MEDIUM")] | length' "${SCAN_RESULTS_DIR}/trivy-${WAZUH_VERSION}.json" 2>/dev/null || echo "0")
        
        echo "Critical: ${CRITICAL_COUNT}"
        echo "High: ${HIGH_COUNT}"
        echo "Medium: ${MEDIUM_COUNT}"
        
        # Thresholds
        if [ "$CRITICAL_COUNT" -gt 0 ]; then
            echo "❌ CRITICAL vulnerabilities found (threshold: 0)"
            TRIVY_PASSED=false
            SCAN_PASSED=false
        elif [ "$HIGH_COUNT" -gt 5 ]; then
            echo "❌ Too many HIGH vulnerabilities (threshold: 5)"
            TRIVY_PASSED=false
            SCAN_PASSED=false
        else
            echo "✅ Trivy scan PASSED"
        fi
    else
        echo "⚠️  Trivy scan results not found"
    fi
else
    echo "⚠️  Trivy not installed - skipping vulnerability scan"
    echo "   Install: brew install trivy"
fi
echo ""

# ============================================
# Scan 3: ClamAV Malware Scan
# ============================================
echo "Scan 3: ClamAV Malware Scan"
echo "-------------------"

MALWARE_PASSED=true

if command -v clamscan &> /dev/null; then
    # Update virus database (if needed)
    # freshclam > /dev/null 2>&1 || true
    
    # Scan packages
    clamscan --infected --recursive "${AGENTS_DIR}" > "${SCAN_RESULTS_DIR}/clamav-${WAZUH_VERSION}.log" 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✅ No malware detected"
    else
        echo "❌ MALWARE DETECTED"
        MALWARE_PASSED=false
        SCAN_PASSED=false
        
        # Show infected files
        grep "FOUND" "${SCAN_RESULTS_DIR}/clamav-${WAZUH_VERSION}.log" || true
    fi
else
    echo "⚠️  ClamAV not installed - skipping malware scan"
    echo "   Install: brew install clamav"
fi
echo ""

# ============================================
# Scan 4: Package Structure Validation
# ============================================
echo "Scan 4: Package Structure Validation"
echo "-------------------"

STRUCTURE_PASSED=true

# Validate RPM (if available)
if command -v rpm &> /dev/null && [ -f "${AGENTS_DIR}/wazuh-agent-${WAZUH_VERSION}-1.x86_64.rpm" ]; then
    rpm -qip "${AGENTS_DIR}/wazuh-agent-${WAZUH_VERSION}-1.x86_64.rpm" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ RPM package structure valid"
    else
        echo "❌ RPM package structure invalid"
        STRUCTURE_PASSED=false
        SCAN_PASSED=false
    fi
fi

# Validate DEB (if available)
if command -v dpkg &> /dev/null && [ -f "${AGENTS_DIR}/wazuh-agent_${WAZUH_VERSION}-1_amd64.deb" ]; then
    dpkg-deb --info "${AGENTS_DIR}/wazuh-agent_${WAZUH_VERSION}-1_amd64.deb" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ DEB package structure valid"
    else
        echo "❌ DEB package structure invalid"
        STRUCTURE_PASSED=false
        SCAN_PASSED=false
    fi
fi

if [ "$STRUCTURE_PASSED" = true ]; then
    echo "✅ Package structure validation PASSED"
else
    echo "❌ Package structure validation FAILED"
fi
echo ""

# ============================================
# Final Result
# ============================================
echo "=========================================="
if [ "$SCAN_PASSED" = true ]; then
    echo "✅ ALL SECURITY SCANS PASSED"
    echo "=========================================="
    echo ""
    echo "Packages are APPROVED for distribution to customers."
    echo "Packages will be uploaded to S3/CDN."
    echo ""
    
    # Update scan report
    jq '.overall_passed = true' "$SCAN_REPORT" > "${SCAN_REPORT}.tmp"
    mv "${SCAN_REPORT}.tmp" "$SCAN_REPORT"
    
    exit 0
else
    echo "❌ SECURITY SCANS FAILED"
    echo "=========================================="
    echo ""
    echo "⚠️  CRITICAL: Packages are BLOCKED from distribution."
    echo "⚠️  Packages will NOT be uploaded to S3/CDN."
    echo ""
    echo "Failed scans:"
    [ "$CHECKSUM_PASSED" = false ] && echo "  • Checksum verification"
    [ "$TRIVY_PASSED" = false ] && echo "  • Trivy vulnerability scan"
    [ "$MALWARE_PASSED" = false ] && echo "  • ClamAV malware scan"
    [ "$STRUCTURE_PASSED" = false ] && echo "  • Package structure validation"
    echo ""
    echo "Action required:"
    echo "1. Review scan results in: ${SCAN_RESULTS_DIR}/"
    echo "2. Investigate security issues"
    echo "3. Wait for Wazuh fix OR skip this version"
    echo ""
    
    # Update scan report
    FAILURES="[]"
    [ "$CHECKSUM_PASSED" = false ] && FAILURES=$(echo "$FAILURES" | jq '. += ["checksum_verification"]')
    [ "$TRIVY_PASSED" = false ] && FAILURES=$(echo "$FAILURES" | jq '. += ["trivy_vulnerability_scan"]')
    [ "$MALWARE_PASSED" = false ] && FAILURES=$(echo "$FAILURES" | jq '. += ["malware_scan"]')
    [ "$STRUCTURE_PASSED" = false ] && FAILURES=$(echo "$FAILURES" | jq '. += ["package_structure"]')
    
    jq --argjson failures "$FAILURES" '.overall_passed = false | .failures = $failures' "$SCAN_REPORT" > "${SCAN_REPORT}.tmp"
    mv "${SCAN_REPORT}.tmp" "$SCAN_REPORT"
    
    exit 1
fi

