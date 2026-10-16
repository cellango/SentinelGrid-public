#!/bin/bash
# EJBCA Initial Setup Script
# This script helps set up EJBCA for SentinelGrid

set -e

EJBCA_URL="${EJBCA_URL:-https://localhost:8443}"
EJBCA_USERNAME="${EJBCA_USERNAME:-admin}"
EJBCA_PASSWORD="${EJBCA_PASSWORD:-admin}"

echo "=========================================="
echo "EJBCA Setup for SentinelGrid"
echo "=========================================="
echo ""
echo "This script will help you set up EJBCA."
echo "EJBCA must be running and accessible."
echo ""
echo "EJBCA URL: $EJBCA_URL"
echo "Username: $EJBCA_USERNAME"
echo ""

# Check if EJBCA is accessible
echo "Checking EJBCA connectivity..."
if curl -k -s -f -u "$EJBCA_USERNAME:$EJBCA_PASSWORD" "$EJBCA_URL/ejbca/ejbca-rest-api/v1/certificate/ca" > /dev/null; then
    echo "✅ EJBCA is accessible"
else
    echo "❌ Cannot connect to EJBCA"
    echo "Please ensure:"
    echo "  1. EJBCA is running: docker-compose up -d ejbca"
    echo "  2. EJBCA is fully started (wait 2-3 minutes)"
    echo "  3. Credentials are correct"
    exit 1
fi

echo ""
echo "=========================================="
echo "EJBCA Setup Instructions"
echo "=========================================="
echo ""
echo "EJBCA requires manual configuration via Admin UI:"
echo ""
echo "1. Access EJBCA Admin UI:"
echo "   URL: $EJBCA_URL/ejbca/adminweb/"
echo "   Username: $EJBCA_USERNAME"
echo "   Password: $EJBCA_PASSWORD"
echo ""
echo "2. Create Root CA:"
echo "   - Navigate to: CA Functions → Create CA"
echo "   - CA Name: SentinelGrid-Root-CA"
echo "   - CA Type: Root CA"
echo "   - Key Algorithm: RSA 4096"
echo "   - Validity: 20 years"
echo ""
echo "3. Create Subordinate CA:"
echo "   - Navigate to: CA Functions → Create CA"
echo "   - CA Name: SentinelGrid-Issuing-CA"
echo "   - CA Type: Sub CA"
echo "   - Signed by: SentinelGrid-Root-CA"
echo "   - Key Algorithm: RSA 2048"
echo "   - Validity: 10 years"
echo ""
echo "4. Create Certificate Profile:"
echo "   - Navigate to: Certificate Profiles → Add"
echo "   - Profile Name: service-tls"
echo "   - CA: SentinelGrid-Issuing-CA"
echo "   - Key Algorithm: RSA 2048"
echo "   - Validity: 90 days"
echo ""
echo "5. Enable REST API:"
echo "   - Navigate to: System Configuration → External RA"
echo "   - Enable REST API"
echo ""
echo "=========================================="
echo "After completing the above steps, run:"
echo "  ./scripts/verify_ejbca_setup.sh"
echo "=========================================="

