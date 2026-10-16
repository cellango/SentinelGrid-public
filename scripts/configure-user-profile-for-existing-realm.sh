#!/bin/bash
# Configure User Profile component for existing Keycloak realm
# This handles the case where realm already exists and import was skipped

set -e

REALM=${1:-agribotsai}
CONTAINER_NAME=${KEYCLOAK_CONTAINER:-sentinelgrid-keycloak-1}

echo "Configuring User Profile for existing realm: $REALM"
echo "=================================================="

docker exec $CONTAINER_NAME bash << EOF
/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin --password admin

echo "Creating User Profile component via JSON file..."
cat > /tmp/user-profile-component.json << 'JSONEOF'
{
  "name": "declarative-user-profile",
  "providerId": "declarative-user-profile",
  "providerType": "org.keycloak.userprofile.UserProfileProvider",
  "parentId": "$REALM",
  "config": {
    "kc.user.profile.config": ["{\\"attributes\\":[],\\"unmanagedAttributePolicy\\":\\"ENABLED\\"}"]
  }
}
JSONEOF

# Create component using JSON file
COMPONENT_ID=\$(/opt/keycloak/bin/kcadm.sh create components -r $REALM -f /tmp/user-profile-component.json -i 2>/dev/null || echo "")

if [ ! -z "\$COMPONENT_ID" ]; then
    echo "✅ User Profile component created (ID: \$COMPONENT_ID)"
else
    echo "⚠️  Component may already exist or creation failed"
    echo "Checking existing components..."
    /opt/keycloak/bin/kcadm.sh get components -r $REALM 2>&1 | grep -i "user-profile\|declarative" || echo "Not found"
fi
EOF

echo ""
echo "✅ User Profile configuration complete!"
echo "You can now set tenant_id and other attributes via API/kcadm.sh"

