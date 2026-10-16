#!/usr/bin/env bash
set -euo pipefail

# Configure demo tenant onboarding via APIs.
# Usage: ./scripts/configure_demo_tenant.sh [TENANT_ID]

TENANT_ID="${1:-1b2eaa87-3407-4761-8edd-9485e945486b}"
API_BASE="${API_BASE:-http://localhost:8082/api/v1}"
IAM_BASE="${IAM_BASE:-http://localhost:8005}"
USER="${TEST_EMAIL:-admin@demo.sentinelgrid.ai}"
PASS="${TEST_PASSWORD:-DemoPassword123!}"

echo "🔑 Fetching token from IAM Agent..."
TOKEN=$(curl -sk -X POST "$IAM_BASE/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$USER\",\"password\":\"$PASS\"}" | jq -r .access_token)

if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
  echo "❌ Failed to obtain token"
  exit 1
fi

HDRS=(-H "Authorization: Bearer $TOKEN" -H "X-Tenant-ID: $TENANT_ID" -H "Content-Type: application/json")

echo "🚀 Running onboarding steps for tenant $TENANT_ID"

echo "1) Identity (SentinelGrid IdP)"
curl -sk "${HDRS[@]}" -X POST "$API_BASE/onboarding/connect-idp" -d '{"idp_mode":"sentinelgrid"}' >/dev/null

echo "2) Cloud (placeholder AWS account)"
curl -sk "${HDRS[@]}" -X POST "$API_BASE/onboarding/connect-aws" -d '{"cloud_provider":"aws","account_id":"111122223333"}' >/dev/null

echo "3) Endpoint (skip actual agent for now)"
# Endpoint connect has a known SQL placeholder bug; skip call to avoid 500

echo "4) Ticketing/SOC (customer-managed SOC, SentinelGrid ticketing default)"
curl -sk "${HDRS[@]}" -X POST "$API_BASE/onboarding/connect-ticketing" \
  -d '{"provider":"sentinelgrid","socManaged":false}' >/dev/null

echo "5) AI proxy (hosted)"
curl -sk "${HDRS[@]}" -X POST "$API_BASE/onboarding/connect-ai" \
  -d '{"mode":"hosted","endpoint_url":"https://example.com/ai","api_key":"ai-key"}' >/dev/null

echo "6) AppSec/Git (enable appsec, skip git creds)"
curl -sk "${HDRS[@]}" -X POST "$API_BASE/onboarding/connect-appsec" -d '{"gateway_url":"https://example.com","api_key":"test","app_id":"demo"}' >/dev/null

echo "7) Tenant readiness / birthright"
# Birthright handled by seed data; no direct API here

echo "✅ Onboarding steps submitted. Status:"
curl -sk "${HDRS[@]}" "$API_BASE/onboarding/status" | jq .
