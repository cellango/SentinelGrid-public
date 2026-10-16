#!/bin/bash
# Quick script to verify tenant_id in tokens

set -e

REALM=${1:-agribotsai}
CLIENT_ID=${2:-agribotsai-web}
USERNAME=${3:-admin@agribotsai.com}
PASSWORD=${4:-ChangeMe123!}

echo "=== Verifying tenant_id in Token ==="
echo "Realm: $REALM"
echo "Username: $USERNAME"
echo ""

# Get token
TOKEN=$(./infra/shared/scripts/get-token.sh "$REALM" "$CLIENT_ID" "$USERNAME" "$PASSWORD" 2>/dev/null | grep "Access Token:" -A 1 | tail -1 | tr -d ' ')

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to get token"
  exit 1
fi

echo "✅ Token retrieved"
echo ""

# Decode token
echo "Token Claims:"
python3 << PYEOF
import base64, json, sys
token = sys.argv[1]
parts = token.split('.')
if len(parts) >= 2:
    payload = parts[1]
    payload += '=' * (4 - len(payload) % 4)
    try:
        decoded = json.loads(base64.urlsafe_b64decode(payload))
        tenant_id = decoded.get('tenant_id')
        print(f"  tenant_id: {tenant_id if tenant_id else '❌ NULL or missing'}")
        print(f"  username: {decoded.get('preferred_username')}")
        print(f"  sub: {decoded.get('sub')}")
        print(f"  roles: {decoded.get('realm_access', {}).get('roles', [])[:3]}")
        if tenant_id:
            print("\n✅ tenant_id is present in token!")
        else:
            print("\n⚠️  tenant_id is missing - check protocol mapper configuration")
    except Exception as e:
        print(f"  Error decoding token: {e}")
PYEOF
"$TOKEN"

echo ""
echo "IAM Agent Validation:"
curl -s -X POST http://localhost:8005/internal/iam/auth/validate-token \
  -H "Content-Type: application/json" \
  -d "{\"token\": \"$TOKEN\"}" | python3 -m json.tool | grep -E "valid|tenant_id|username|error" | head -5

