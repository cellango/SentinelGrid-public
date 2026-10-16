#!/bin/bash
# Test if we can insert attributes directly into the database

echo "======================================================================="
echo "  Testing Direct Database Attribute Insertion"
echo "======================================================================="

# Create a test user via API
echo -e "\n1. Creating test user via Keycloak API..."
USER_ID=$(docker exec sentinelgrid-keycloak-1 bash -c "/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin --password admin && /opt/keycloak/bin/kcadm.sh create users -r sentinelgrid -s username=dbtest@example.com -s email=dbtest@example.com -s firstName=DB -s lastName=Test -s enabled=true -i")

echo "✅ User created: $USER_ID"

# Insert attribute directly into database
echo -e "\n2. Inserting tenant_id attribute directly into database..."
TENANT_ID="test-tenant-$(uuidgen | tr '[:upper:]' '[:lower:]')"
ATTR_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')

docker exec sentinelgrid-keycloak_db-1 psql -U keycloak -d keycloak -c "
INSERT INTO user_attribute (id, name, value, user_id) 
VALUES ('$ATTR_ID', 'tenant_id', '$TENANT_ID', '$USER_ID');
"

echo "✅ Attribute inserted into database"
echo "   tenant_id = $TENANT_ID"

# Verify in database
echo -e "\n3. Verifying attribute in database..."
docker exec sentinelgrid-keycloak_db-1 psql -U keycloak -d keycloak -c "
SELECT name, value FROM user_attribute WHERE user_id = '$USER_ID';
"

# Query user via Keycloak API
echo -e "\n4. Querying user via Keycloak API to see if attribute appears..."
ATTRS=$(docker exec sentinelgrid-keycloak-1 bash -c "/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin --password admin && /opt/keycloak/bin/kcadm.sh get users/$USER_ID -r sentinelgrid --fields attributes")

echo "$ATTRS"

if echo "$ATTRS" | grep -q "$TENANT_ID"; then
    echo -e "\n✅✅✅ SUCCESS! Attribute appears in API after database insert!"
else
    echo -e "\n❌ Attribute NOT appearing in API even after database insert"
fi

# Get a token to test
echo -e "\n5. Setting password and testing token..."
docker exec sentinelgrid-keycloak-1 bash -c "/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin --password admin && /opt/keycloak/bin/kcadm.sh set-password -r sentinelgrid --username dbtest@example.com --new-password 'Test123!' --no-temporary"

echo "✅ Password set"

# Test getting token
echo -e "\n6. Getting JWT token..."
curl -s -X POST 'http://localhost:8080/realms/sentinelgrid/protocol/openid-connect/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'client_id=sentinelgrid-web&username=dbtest@example.com&password=Test123!&grant_type=password' \
  | jq -r '.access_token' | cut -d'.' -f2 | base64 -d 2>/dev/null | jq '.tenant_id'

# Cleanup
echo -e "\n7. Cleanup..."
docker exec sentinelgrid-keycloak-1 bash -c "/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin --password admin && /opt/keycloak/bin/kcadm.sh delete users/$USER_ID -r sentinelgrid"

echo -e "\n✅ Test complete"

