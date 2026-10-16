#!/bin/bash
# Verify EJBCA Setup
# Checks if EJBCA is properly configured for SentinelGrid

set -e

EJBCA_URL="${EJBCA_URL:-https://localhost:8443}"
EJBCA_USERNAME="${EJBCA_USERNAME:-admin}"
EJBCA_PASSWORD="${EJBCA_PASSWORD:-admin}"
CA_NAME="${EJBCA_CA_NAME:-SentinelGrid-Issuing-CA}"

echo "=========================================="
echo "EJBCA Setup Verification"
echo "=========================================="
echo ""

# Check connectivity
echo "1. Checking EJBCA connectivity..."
if curl -k -s -f -u "$EJBCA_USERNAME:$EJBCA_PASSWORD" "$EJBCA_URL/ejbca/ejbca-rest-api/v1/certificate/ca" > /dev/null; then
    echo "   ✅ EJBCA is accessible"
else
    echo "   ❌ Cannot connect to EJBCA"
    exit 1
fi

# Check if CA exists
echo "2. Checking if CA '$CA_NAME' exists..."
CA_LIST=$(curl -k -s -u "$EJBCA_USERNAME:$EJBCA_PASSWORD" "$EJBCA_URL/ejbca/ejbca-rest-api/v1/certificate/ca" | grep -i "$CA_NAME" || true)
if [ -n "$CA_LIST" ]; then
    echo "   ✅ CA '$CA_NAME' found"
else
    echo "   ❌ CA '$CA_NAME' not found"
    echo "   Please create the CA in EJBCA Admin UI"
    exit 1
fi

# Check if we can get CA certificate
echo "3. Checking CA certificate retrieval..."
if curl -k -s -f -u "$EJBCA_USERNAME:$EJBCA_PASSWORD" "$EJBCA_URL/ejbca/ejbca-rest-api/v1/ca/$CA_NAME/certificate" > /dev/null; then
    echo "   ✅ Can retrieve CA certificate"
else
    echo "   ❌ Cannot retrieve CA certificate"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ EJBCA Setup Verified"
echo "=========================================="
echo ""
echo "EJBCA is ready for use with SentinelGrid!"
echo ""
echo "Next steps:"
echo "  1. Test certificate issuance via cert_service API"
echo "  2. Configure certificate profiles"
echo "  3. Set up multi-tenant CAs (Phase 2)"

