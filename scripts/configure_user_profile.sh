#!/bin/bash
# Configure Keycloak User Profile with custom attributes
# Required for Keycloak v25+ to persist tenant_id and customer_id

set -e

KEYCLOAK_URL="${KEYCLOAK_URL:-https://identity.sentinelgrid.ai:8443}"
REALM="${KEYCLOAK_REALM:-sentinelgrid}"
ADMIN_USER="${KEYCLOAK_ADMIN_USER:-admin}"
ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-admin}"

echo "======================================================================="
echo "  Configuring Keycloak User Profile for SentinelGrid"
echo "======================================================================="
echo ""
echo "Keycloak URL: $KEYCLOAK_URL"
echo "Realm: $REALM"
echo ""

# Check if running inside container or outside
if [ -f "/.dockerenv" ]; then
    # Inside container
    KCADM="/opt/keycloak/bin/kcadm.sh"
else
    # Outside container
    CONTAINER=$(docker ps --filter "name=keycloak" --format "{{.Names}}" | head -1)
    if [ -z "$CONTAINER" ]; then
        echo "❌ Keycloak container not found"
        exit 1
    fi
    KCADM="docker exec $CONTAINER /opt/keycloak/bin/kcadm.sh"
fi

echo "1. Authenticating with Keycloak..."
$KCADM config credentials --server $KEYCLOAK_URL --realm master --user $ADMIN_USER --password $ADMIN_PASSWORD
echo "✅ Authenticated"

echo ""
echo "2. Updating User Profile with custom attributes..."

# Create User Profile configuration with tenant_id and customer_id
$KCADM update realms/$REALM/users/profile -r $REALM -f - << 'EOF'
{
  "attributes": [
    {
      "name": "username",
      "displayName": "${username}",
      "validations": {
        "length": {"min": 3, "max": 255},
        "username-prohibited-characters": {},
        "up-username-not-idn-homograph": {}
      },
      "permissions": {"view": ["admin", "user"], "edit": ["admin", "user"]},
      "multivalued": false
    },
    {
      "name": "email",
      "displayName": "${email}",
      "validations": {"email": {}, "length": {"max": 255}},
      "required": {"roles": ["user"]},
      "permissions": {"view": ["admin", "user"], "edit": ["admin", "user"]},
      "multivalued": false
    },
    {
      "name": "firstName",
      "displayName": "${firstName}",
      "validations": {"length": {"max": 255}, "person-name-prohibited-characters": {}},
      "required": {"roles": ["user"]},
      "permissions": {"view": ["admin", "user"], "edit": ["admin", "user"]},
      "multivalued": false
    },
    {
      "name": "lastName",
      "displayName": "${lastName}",
      "validations": {"length": {"max": 255}, "person-name-prohibited-characters": {}},
      "required": {"roles": ["user"]},
      "permissions": {"view": ["admin", "user"], "edit": ["admin", "user"]},
      "multivalued": false
    },
    {
      "name": "tenant_id",
      "displayName": "Tenant ID",
      "validations": {},
      "annotations": {
        "description": "Universal tenant isolation boundary for multi-tenancy"
      },
      "permissions": {"view": ["admin"], "edit": ["admin"]},
      "multivalued": false
    },
    {
      "name": "customer_id",
      "displayName": "Customer ID",
      "validations": {},
      "annotations": {
        "description": "Customer identifier for billing and organization"
      },
      "permissions": {"view": ["admin"], "edit": ["admin"]},
      "multivalued": false
    }
  ],
  "groups": [
    {"name": "user-metadata", "displayHeader": "User metadata", "displayDescription": "Attributes for user metadata"}
  ]
}
EOF

echo "✅ User Profile updated with tenant_id and customer_id"

echo ""
echo "3. Verifying User Profile configuration..."
$KCADM get realms/$REALM/users/profile -r $REALM | grep -E "(tenant_id|customer_id)" && echo "✅ Custom attributes confirmed in User Profile"

echo ""
echo "======================================================================="
echo "  ✅ User Profile Configuration Complete!"
echo "======================================================================="
echo ""
echo "Custom attributes added:"
echo "  - tenant_id: Universal tenant isolation boundary"
echo "  - customer_id: Customer identifier"
echo ""
echo "These attributes will now persist when creating/updating users."
echo ""
