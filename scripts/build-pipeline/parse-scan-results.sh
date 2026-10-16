#!/bin/bash
# Parse scan results and determine pass/fail
# This script parses scan results and determines if image passes security policy

set -e

SCAN_RESULT_FILE="${1:-}"

if [ -z "$SCAN_RESULT_FILE" ] || [ ! -f "$SCAN_RESULT_FILE" ]; then
    echo "Usage: $0 <scan_result_file>"
    exit 1
fi

# Security policy thresholds
MAX_CRITICAL=0
MAX_HIGH=5
MAX_MEDIUM=20
MAX_LOW=50

echo "Parsing scan results: ${SCAN_RESULT_FILE}"

# Extract vulnerability counts
if command -v jq &> /dev/null; then
    CRITICAL=$(jq -r '.vulnerability_count.critical // 0' "$SCAN_RESULT_FILE")
    HIGH=$(jq -r '.vulnerability_count.high // 0' "$SCAN_RESULT_FILE")
    MEDIUM=$(jq -r '.vulnerability_count.medium // 0' "$SCAN_RESULT_FILE")
    LOW=$(jq -r '.vulnerability_count.low // 0' "$SCAN_RESULT_FILE")
    SCAN_STATUS=$(jq -r '.scan_status // "unknown"' "$SCAN_RESULT_FILE")
else
    # Fallback: use grep/sed if jq not available
    CRITICAL=$(grep -o '"critical":[0-9]*' "$SCAN_RESULT_FILE" | grep -o '[0-9]*' || echo "0")
    HIGH=$(grep -o '"high":[0-9]*' "$SCAN_RESULT_FILE" | grep -o '[0-9]*' || echo "0")
    MEDIUM=$(grep -o '"medium":[0-9]*' "$SCAN_RESULT_FILE" | grep -o '[0-9]*' || echo "0")
    LOW=$(grep -o '"low":[0-9]*' "$SCAN_RESULT_FILE" | grep -o '[0-9]*' || echo "0")
    SCAN_STATUS=$(grep -o '"scan_status":"[^"]*"' "$SCAN_RESULT_FILE" | cut -d'"' -f4 || echo "unknown")
fi

echo ""
echo "Vulnerability Summary:"
echo "  Critical: ${CRITICAL} (max: ${MAX_CRITICAL})"
echo "  High: ${HIGH} (max: ${MAX_HIGH})"
echo "  Medium: ${MEDIUM} (max: ${MAX_MEDIUM})"
echo "  Low: ${LOW} (max: ${MAX_LOW})"
echo ""

# Check against policy
PASS=true
REASONS=()

if [ "$CRITICAL" -gt "$MAX_CRITICAL" ]; then
    PASS=false
    REASONS+=("Critical vulnerabilities exceed threshold: ${CRITICAL} > ${MAX_CRITICAL}")
fi

if [ "$HIGH" -gt "$MAX_HIGH" ]; then
    PASS=false
    REASONS+=("High vulnerabilities exceed threshold: ${HIGH} > ${MAX_HIGH}")
fi

if [ "$MEDIUM" -gt "$MAX_MEDIUM" ]; then
    PASS=false
    REASONS+=("Medium vulnerabilities exceed threshold: ${MEDIUM} > ${MAX_MEDIUM}")
fi

if [ "$LOW" -gt "$MAX_LOW" ]; then
    PASS=false
    REASONS+=("Low vulnerabilities exceed threshold: ${LOW} > ${MAX_LOW}")
fi

if [ "$SCAN_STATUS" != "passed" ]; then
    PASS=false
    REASONS+=("Scan status is not 'passed': ${SCAN_STATUS}")
fi

# Output result
if [ "$PASS" = true ]; then
    echo "✅ Scan PASSED - Image meets security policy"
    exit 0
else
    echo "❌ Scan FAILED - Image does not meet security policy"
    echo ""
    echo "Reasons:"
    for reason in "${REASONS[@]}"; do
        echo "  - ${reason}"
    done
    exit 1
fi

