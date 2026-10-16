#!/bin/bash
# Debug script for User Profile component creation
# Adds extensive logging and error checking

set -e

REALM=${1:-agribotsai}
CONTAINER_NAME=${KEYCLOAK_CONTAINER:-sentinelgrid-keycloak-1}

echo "=================================================="
echo "DEBUG: User Profile Component Creation"
echo "Realm: $REALM"
echo "=================================================="
echo ""

docker exec $CONTAINER_NAME bash << 'DEBUGSCRIPT'
/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin --password admin

REALM="'$REALM'"

echo "Step 1: Getting realm ID..."
REALM_ID=$(/opt/keycloak/bin/kcadm.sh get realms/$REALM --fields id --format csv --noquotes 2>&1 | tail -1)
if [ -z "$REALM_ID" ]; then
    echo "❌ ERROR: Could not get realm ID"
    exit 1
fi
echo "✅ Realm ID: $REALM_ID"
echo ""

echo "Step 2: Checking existing components..."
echo "Current components:"
/opt/keycloak/bin/kcadm.sh get components -r $REALM 2>&1 | grep -i "providerId" | head -10
echo ""

echo "Step 3: Checking if User Profile component already exists..."
EXISTING=$(/opt/keycloak/bin/kcadm.sh get components -r $REALM 2>&1 | grep -i "declarative-user-profile" || echo "")
if [ ! -z "$EXISTING" ]; then
    echo "⚠️  User Profile component may already exist!"
    echo "$EXISTING" | head -5
    exit 0
fi
echo "✅ No existing User Profile component found"
echo ""

echo "Step 4: Creating User Profile component JSON..."
cat > /tmp/user-profile-debug.json << 'JSONEOF'
{
  "name": "declarative-user-profile",
  "providerId": "declarative-user-profile",
  "providerType": "org.keycloak.userprofile.UserProfileProvider",
  "parentId": "REALM_ID_PLACEHOLDER",
  "config": {
    "kc.user.profile.config": ["{\"attributes\":[],\"unmanagedAttributePolicy\":\"ENABLED\"}"]
  }
}
JSONEOF

# Replace placeholder with actual realm ID
sed -i "s/REALM_ID_PLACEHOLDER/$REALM_ID/g" /tmp/user-profile-debug.json

echo "Component JSON:"
cat /tmp/user-profile-debug.json
echo ""

echo "Step 5: Attempting to create component..."
echo "Command: /opt/keycloak/bin/kcadm.sh create components -r $REALM -f /tmp/user-profile-debug.json"
RESULT=$(/opt/keycloak/bin/kcadm.sh create components -r $REALM -f /tmp/user-profile-debug.json -i 2>&1)
EXIT_CODE=$?

echo "Exit code: $EXIT_CODE"
echo "Output: $RESULT"
echo ""

if [ $EXIT_CODE -eq 0 ] && [ ! -z "$RESULT" ]; then
    echo "✅ Component created! ID: $RESULT"
    echo ""
    echo "Step 6: Verifying component..."
    /opt/keycloak/bin/kcadm.sh get components -r $REALM 2>&1 | grep -i "declarative-user-profile" || echo "⚠️  Not found in list"
else
    echo "❌ Component creation failed"
    echo "Full error output:"
    echo "$RESULT"
    echo ""
    echo "Step 6: Trying alternative method - using -s flags..."
    echo "Command: /opt/keycloak/bin/kcadm.sh create components -r $REALM -s name=declarative-user-profile -s providerId=declarative-user-profile -s providerType=org.keycloak.userprofile.UserProfileProvider -s parentId=$REALM_ID"
    
    # Try with -s flags
    ALT_RESULT=$(/opt/keycloak/bin/kcadm.sh create components -r $REALM \
        -s name=declarative-user-profile \
        -s providerId=declarative-user-profile \
        -s providerType=org.keycloak.userprofile.UserProfileProvider \
        -s "parentId=$REALM_ID" \
        -s 'config.kc.user.profile.config=["{\"attributes\":[],\"unmanagedAttributePolicy\":\"ENABLED\"}"]' \
        -i 2>&1)
    
    echo "Alternative method output: $ALT_RESULT"
fi

echo ""
echo "=================================================="
echo "DEBUG COMPLETE"
echo "=================================================="
DEBUGSCRIPT

