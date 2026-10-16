#!/bin/bash
# Create dedicated SentinelGrid admin account in Keycloak
# This account will be used by IAM Agent instead of default admin

set -e

KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
ADMIN_USER="${KEYCLOAK_ADMIN_USER:-admin}"
ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
NEW_USERNAME="sentinelgrid-admin"
NEW_PASSWORD="SentinelGridAdmin2024!"

echo "Creating SentinelGrid admin account..."

# Configure kcadm credentials
docker-compose -f docker-compose.dev.yml exec -T keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 \
  --realm master \
  --user "$ADMIN_USER" \
  --password "$ADMIN_PASSWORD" > /dev/null 2>&1

# Check if user already exists
EXISTING=$(docker-compose -f docker-compose.dev.yml exec -T keycloak /opt/keycloak/bin/kcadm.sh get users -r master -q username="$NEW_USERNAME" --format json 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print('EXISTS' if data else 'NOT_FOUND')" 2>/dev/null || echo "NOT_FOUND")

if [ "$EXISTING" = "EXISTS" ]; then
  echo "User $NEW_USERNAME already exists. Updating password..."
  docker-compose -f docker-compose.dev.yml exec -T keycloak /opt/keycloak/bin/kcadm.sh set-password \
    -r master \
    --username "$NEW_USERNAME" \
    --new-password "$NEW_PASSWORD" > /dev/null 2>&1
  echo "✅ Password updated for existing user"
else
  echo "Creating new user..."
  docker-compose -f docker-compose.dev.yml exec -T keycloak /opt/keycloak/bin/kcadm.sh create users -r master \
    -s username="$NEW_USERNAME" \
    -s enabled=true \
    -s email=sentinelgrid-admin@sentinelgrid.local \
    -s firstName=SentinelGrid \
    -s lastName=Admin > /dev/null 2>&1
  
  echo "Setting password..."
  docker-compose -f docker-compose.dev.yml exec -T keycloak /opt/keycloak/bin/kcadm.sh set-password \
    -r master \
    --username "$NEW_USERNAME" \
    --new-password "$NEW_PASSWORD" > /dev/null 2>&1
  
  echo "Assigning admin role..."
  docker-compose -f docker-compose.dev.yml exec -T keycloak /opt/keycloak/bin/kcadm.sh add-roles \
    -r master \
    --uusername "$NEW_USERNAME" \
    --rolename admin > /dev/null 2>&1
  
  echo "✅ User created successfully"
fi

echo ""
echo "Account Details:"
echo "  Username: $NEW_USERNAME"
echo "  Password: $NEW_PASSWORD"
echo "  Email: sentinelgrid-admin@sentinelgrid.local"
echo ""
echo "⚠️  IMPORTANT: Update docker-compose.dev.yml with these credentials:"
echo "  KEYCLOAK_ADMIN_USER=$NEW_USERNAME"
echo "  KEYCLOAK_ADMIN_PASSWORD=$NEW_PASSWORD"
echo ""

