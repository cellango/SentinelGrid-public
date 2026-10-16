#!/bin/bash
# Configure User Profile attribute via Admin REST API (runs inside Keycloak container)

set -e

REALM=${1:-agribotsai}
ATTRIBUTE_NAME=${2:-tenant_id}
CONTAINER_NAME=${KEYCLOAK_CONTAINER:-sentinelgrid-keycloak-1}

echo "Configuring User Profile attribute '$ATTRIBUTE_NAME' in realm '$REALM'"
echo "Using Admin REST API via internal Docker network..."

docker exec $CONTAINER_NAME bash -c "
# Get admin token
ADMIN_TOKEN=\$(curl -s -X POST 'http://localhost:8080/realms/master/protocol/openid-connect/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'client_id=admin-cli&username=admin&password=admin&grant_type=password' | \
  python3 -c 'import sys,json; print(json.load(sys.stdin)[\"access_token\"])')

echo \"✅ Admin token obtained\"

# Get current User Profile configuration
echo \"Getting current User Profile configuration...\"
PROFILE_CONFIG=\$(curl -s -X GET \"http://localhost:8080/admin/realms/$REALM/users/profile\" \
  -H \"Authorization: Bearer \$ADMIN_TOKEN\" \
  -H \"Content-Type: application/json\" 2>/dev/null)

if [ \$? -eq 0 ] && [ ! -z \"\$PROFILE_CONFIG\" ]; then
    echo \"✅ Got User Profile config\"
    echo \"Current config:\"
    echo \"\$PROFILE_CONFIG\" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(json.dumps(d, indent=2)[:500])' 2>/dev/null || echo \"\$PROFILE_CONFIG\"
    
    # Add tenant_id attribute to configuration
    echo \"Adding $ATTRIBUTE_NAME attribute...\"
    UPDATED_CONFIG=\$(echo \"\$PROFILE_CONFIG\" | python3 << PYEOF
import sys, json
config = json.load(sys.stdin)
if 'attributes' not in config:
    config['attributes'] = {}
if '$ATTRIBUTE_NAME' not in config['attributes']:
    config['attributes']['$ATTRIBUTE_NAME'] = {
        'name': '$ATTRIBUTE_NAME',
        'displayName': 'Tenant ID',
        'required': False,
        'permissions': {'view': ['admin', 'user'], 'edit': ['admin']},
        'validations': {}
    }
print(json.dumps(config))
PYEOF
)
    
    # Update User Profile configuration
    HTTP_CODE=\$(curl -s -w \"%{http_code}\" -o /tmp/profile_response.json \
      -X PUT \"http://localhost:8080/admin/realms/$REALM/users/profile\" \
      -H \"Authorization: Bearer \$ADMIN_TOKEN\" \
      -H \"Content-Type: application/json\" \
      -d \"\$UPDATED_CONFIG\")
    
    if [ \"\$HTTP_CODE\" = \"200\" ] || [ \"\$HTTP_CODE\" = \"204\" ]; then
        echo \"✅✅✅ User Profile configured successfully!\"
        exit 0
    else
        echo \"❌ Failed to update User Profile (HTTP \$HTTP_CODE)\"
        cat /tmp/profile_response.json
        exit 1
    fi
else
    echo \"⚠️  Could not access User Profile API endpoint\"
    echo \"Response: \$PROFILE_CONFIG\"
    echo \"\"
    echo \"This may mean:"
    echo \"  1. Endpoint path is different in Keycloak 26.x\"
    echo \"  2. Requires Admin Console UI configuration\"
    echo \"  3. Different authentication method needed\"
    exit 1
fi
"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ User Profile configured! Now try setting the attribute on a user."
else
    echo ""
    echo "❌ Could not configure User Profile via API"
    echo "📝 Fallback: Use Admin Console UI to configure:"
    echo "   http://localhost:8081/admin → Realm Settings → User Profile"
fi

