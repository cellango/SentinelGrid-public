#!/bin/bash
# Quick test script for token validation API endpoint
# Usage: ./test_api_endpoint.sh

set -e

echo "🔍 Testing Token Validation API Endpoint"
echo "=========================================="

# Get token
echo "1️⃣  Getting token from Keycloak..."
TOKEN=$(./infra/shared/scripts/get-token.sh agribotsai agribotsai-web admin@agribotsai.com ChangeMe123! 2>/dev/null | grep "Access Token:" -A 1 | tail -1 | tr -d ' ')

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to get token"
    exit 1
fi

echo "✅ Token obtained"

# Test API endpoint
echo ""
echo "2️⃣  Testing /validate-token endpoint..."
RESPONSE=$(curl -s -X POST http://localhost:8005/internal/iam/auth/validate-token \
    -H "Content-Type: application/json" \
    -d "{\"token\": \"$TOKEN\"}")

echo "$RESPONSE" | jq '.'

# Check result
VALID=$(echo "$RESPONSE" | jq -r '.valid')
if [ "$VALID" = "true" ]; then
    echo ""
    echo "✅ Token validation SUCCESSFUL!"
    echo "   Username: $(echo "$RESPONSE" | jq -r '.username')"
    echo "   Tenant ID: $(echo "$RESPONSE" | jq -r '.tenant_id')"
    echo "   Roles: $(echo "$RESPONSE" | jq -r '.roles | join(", ")')"
    exit 0
else
    echo ""
    echo "❌ Token validation FAILED"
    echo "   Error: $(echo "$RESPONSE" | jq -r '.error')"
    exit 1
fi

