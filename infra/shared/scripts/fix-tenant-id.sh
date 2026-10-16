#!/bin/bash
# Script to properly set tenant_id user attribute in Keycloak
set -e

REALM=${1:-agribotsai}
TENANT_UUID=${2}
USERNAME=${3:-admin@agribotsai.com}

if [ -z "$TENANT_UUID" ]; then
  echo "Usage: ./fix-tenant-id.sh <realm> <tenant_uuid> [username]"
  exit 1
fi

KEYCLOAK_URL=http://localhost:8081

echo "Setting tenant_id=$TENANT_UUID for user $USERNAME in realm $REALM"

# Get user ID
USER_ID=$(docker-compose -f docker-compose.dev.yml exec -T keycloak /opt/keycloak/bin/kcadm.sh get users -r $REALM -q username="$USERNAME" --fields id --format csv --noquotes 2>&1 | tail -1)

if [ -z "$USER_ID" ]; then
  echo "❌ User not found"
  exit 1
fi

echo "User ID: $USER_ID"

# Set attribute using JSON format
docker-compose -f docker-compose.dev.yml exec -T keycloak /opt/keycloak/bin/kcadm.sh update users/"$USER_ID" -r $REALM \
  -b "{\"attributes\": {\"tenant_id\": [\"$TENANT_UUID\"]}}" 2>&1

echo "✅ Updated tenant_id attribute"
echo ""
echo "Now generate a new token to see tenant_id in claims"

