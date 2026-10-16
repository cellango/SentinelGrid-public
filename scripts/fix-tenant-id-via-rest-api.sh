#!/bin/bash
# Fix tenant_id attribute using Admin REST API (works inside Keycloak container)
# This approach uses the internal Docker network to bypass HTTPS requirement

set -e

REALM=${1:-agribotsai}
USERNAME=${2:-admin@agribotsai.com}
TENANT_UUID=${3:-""}

if [ -z "$TENANT_UUID" ]; then
    echo "Usage: $0 <realm> <username> <tenant_uuid>"
    exit 1
fi

CONTAINER_NAME=${KEYCLOAK_CONTAINER:-sentinelgrid-keycloak-1}

echo "Setting tenant_id=$TENANT_UUID for user $USERNAME in realm $REALM"
echo "Using Admin REST API via internal Docker network..."

# Get user ID and update via REST API inside container
docker exec $CONTAINER_NAME bash -c "
# Get admin token
ADMIN_TOKEN=\$(curl -s -X POST 'http://localhost:8080/realms/master/protocol/openid-connect/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'client_id=admin-cli&username=admin&password=admin&grant_type=password' | \
  python3 -c 'import sys,json; print(json.load(sys.stdin)[\"access_token\"])')

# Get user ID
USER_JSON=\$(curl -s -X GET \"http://localhost:8080/admin/realms/$REALM/users?username=$USERNAME\" \
  -H \"Authorization: Bearer \$ADMIN_TOKEN\")

USER_ID=\$(echo \"\$USER_JSON\" | python3 -c 'import sys,json; users=json.load(sys.stdin); print(users[0][\"id\"] if isinstance(users, list) and len(users) > 0 else \"\")')

if [ -z \"\$USER_ID\" ]; then
    echo \"❌ User $USERNAME not found\"
    exit 1
fi

echo \"User ID: \$USER_ID\"

# Get current user data
USER_DATA=\$(curl -s -X GET \"http://localhost:8080/admin/realms/$REALM/users/\$USER_ID\" \
  -H \"Authorization: Bearer \$ADMIN_TOKEN\")

# Update with tenant_id attribute
UPDATED_DATA=\$(echo \"\$USER_DATA\" | python3 << PYEOF
import sys, json
user = json.load(sys.stdin)
user['attributes'] = {'tenant_id': ['$TENANT_UUID']}
# Remove read-only fields
for key in ['access', 'self', 'id', 'createdTimestamp']:
    user.pop(key, None)
print(json.dumps(user))
PYEOF
)

# Update user
HTTP_CODE=\$(curl -s -w \"%{http_code}\" -o /tmp/update_response.json \
  -X PUT \"http://localhost:8080/admin/realms/$REALM/users/\$USER_ID\" \
  -H \"Authorization: Bearer \$ADMIN_TOKEN\" \
  -H \"Content-Type: application/json\" \
  -d \"\$UPDATED_DATA\")

if [ \"\$HTTP_CODE\" = \"204\" ] || [ \"\$HTTP_CODE\" = \"200\" ]; then
    echo \"✅ User updated successfully (HTTP \$HTTP_CODE)\"
    
    # Verify
    sleep 1
    VERIFY_DATA=\$(curl -s -X GET \"http://localhost:8080/admin/realms/$REALM/users/\$USER_ID\" \
      -H \"Authorization: Bearer \$ADMIN_TOKEN\")
    
    ATTRIBUTES=\$(echo \"\$VERIFY_DATA\" | python3 -c 'import sys,json; user=json.load(sys.stdin); print(json.dumps(user.get(\"attributes\", {})))')
    
    TENANT_ID_VALUE=\$(echo \"\$ATTRIBUTES\" | python3 -c 'import sys,json; attrs=json.load(sys.stdin); print(attrs.get(\"tenant_id\", [None])[0] if attrs.get(\"tenant_id\") else None)')
    
    if [ \"\$TENANT_ID_VALUE\" = \"$TENANT_UUID\" ]; then
        echo \"✅✅✅ SUCCESS! tenant_id attribute persisted: \$TENANT_ID_VALUE\"
        exit 0
    else
        echo \"⚠️  Warning: Attribute may not have persisted correctly\"
        echo \"Attributes: \$ATTRIBUTES\"
        exit 1
    fi
else
    echo \"❌ Failed to update user (HTTP \$HTTP_CODE)\"
    cat /tmp/update_response.json
    exit 1
fi
"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Done! Generate a new token to verify tenant_id appears in JWT."
else
    echo ""
    echo "❌ Failed to set tenant_id attribute"
    exit 1
fi

