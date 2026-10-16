#!/bin/bash
# Configure User Profile attribute via kcadm.sh (inside Keycloak container)

set -e

REALM=${1:-agribotsai}
ATTRIBUTE_NAME=${2:-tenant_id}

echo "Configuring User Profile attribute '$ATTRIBUTE_NAME' in realm '$REALM'"
echo "This may require accessing Admin Console UI if kcadm.sh doesn't support it"

CONTAINER_NAME=${KEYCLOAK_CONTAINER:-sentinelgrid-keycloak-1}

# Try to get User Profile config
docker exec $CONTAINER_NAME bash -c "
/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin --password admin

echo 'Checking if User Profile API is accessible via kcadm...'

# Try getting User Profile config
/opt/keycloak/bin/kcadm.sh get realms/$REALM/user-profile/config -r $REALM 2>&1 || echo 'User Profile endpoint not found via kcadm'

echo ''
echo '⚠️  If kcadm.sh doesn't support User Profile configuration:'
echo '   1. Access Admin Console: http://localhost:8081/admin'
echo '   2. Navigate to: Realm Settings → User Profile'
echo '   3. Click \"Create Attribute\" or edit existing'
echo '   4. Add attribute name: $ATTRIBUTE_NAME'
echo '   5. Set validation/constraints as needed'
echo '   6. Save configuration'
"

