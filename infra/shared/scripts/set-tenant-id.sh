#!/bin/bash
# Script to set tenant_id attribute for AgribotsAI users in Keycloak
# Usage: ./set-tenant-id.sh <realm> <tenant_uuid> [username]

set -e

REALM=${1:-agribotsai}
TENANT_UUID=${2}
USERNAME=${3}

if [ -z "$TENANT_UUID" ]; then
  echo "Usage: ./set-tenant-id.sh <realm> <tenant_uuid> [username]"
  echo ""
  echo "Examples:"
  echo "  # Set tenant_id for all users in realm"
  echo "  ./set-tenant-id.sh agribotsai $(uuidgen)"
  echo ""
  echo "  # Set tenant_id for specific user"
  echo "  ./set-tenant-id.sh agribotsai $(uuidgen) admin@agribotsai.com"
  exit 1
fi

KEYCLOAK_URL=${KEYCLOAK_URL:-http://localhost:8081}
KEYCLOAK_ADMIN_USER=${KEYCLOAK_ADMIN_USER:-admin}
KEYCLOAK_ADMIN_PASSWORD=${KEYCLOAK_ADMIN_PASSWORD:-admin}

echo "=========================================="
echo "Setting tenant_id for AgribotsAI users"
echo "=========================================="
echo "Realm: $REALM"
echo "Tenant UUID: $TENANT_UUID"
echo "Keycloak URL: $KEYCLOAK_URL"
echo ""

# Check if kcadm.sh is available
if ! command -v kcadm.sh &> /dev/null; then
  echo "❌ kcadm.sh not found. Please install Keycloak Admin CLI."
  echo "   Download from: https://www.keycloak.org/downloads"
  exit 1
fi

# Authenticate to the master realm
echo "Authenticating to Keycloak..."
kcadm.sh config credentials --server "$KEYCLOAK_URL" --realm master --user "$KEYCLOAK_ADMIN_USER" --password "$KEYCLOAK_ADMIN_PASSWORD"

if [ -n "$USERNAME" ]; then
  # Update specific user
  echo "Updating tenant_id for user: $USERNAME"
  USER_ID=$(kcadm.sh get users -r "$REALM" -q username="$USERNAME" --fields id --format csv --noquotes | tail -1)
  
  if [ -z "$USER_ID" ]; then
    echo "❌ User $USERNAME not found in realm $REALM"
    exit 1
  fi
  
  kcadm.sh update users/"$USER_ID" -r "$REALM" -s "attributes.tenant_id=[\"$TENANT_UUID\"]"
  echo "✅ Updated tenant_id for user $USERNAME"
else
  # Update all users in realm
  echo "Updating tenant_id for all users in realm $REALM..."
  
  USERNAMES=$(kcadm.sh get users -r "$REALM" --fields username --format csv --noquotes | tail -n +2)
  
  if [ -z "$USERNAMES" ]; then
    echo "⚠️  No users found in realm $REALM"
    exit 0
  fi
  
  COUNT=0
  while IFS= read -r username; do
    if [ -n "$username" ]; then
      USER_ID=$(kcadm.sh get users -r "$REALM" -q username="$username" --fields id --format csv --noquotes | tail -1)
      if [ -n "$USER_ID" ]; then
        kcadm.sh update users/"$USER_ID" -r "$REALM" -s "attributes.tenant_id=[\"$TENANT_UUID\"]"
        echo "  ✅ Updated tenant_id for user: $username"
        COUNT=$((COUNT + 1))
      fi
    fi
  done <<< "$USERNAMES"
  
  echo ""
  echo "✅ Updated tenant_id for $COUNT users"
fi

echo ""
echo "=========================================="
echo "✅ Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Generate a new token to get tenant_id in claims"
echo "   ./get-token.sh $REALM ${REALM}-web admin@agribotsai.com ChangeMe123!"
echo ""
echo "2. Test token validation"
echo "   curl -X POST http://localhost:8005/internal/iam/auth/validate-token \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"token\": \"<token>\"}' | jq"

