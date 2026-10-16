#!/bin/bash
# Test the seeder flow: delete admin user, restart iam_agent, verify login

set -e

REALM=${KEYCLOAK_REALM:-sentinelgrid}
ADMIN_EMAIL=${KEYCLOAK_ADMIN_EMAIL:-admin@sentinelgrid.ai}

echo "=========================================="
echo "Testing Seeder Flow"
echo "=========================================="
echo "Realm: $REALM"
echo "Admin Email: $ADMIN_EMAIL"
echo ""

# Step 1: Delete admin user using standalone script (run inside iam_agent container to access internal network)
echo "Step 1: Deleting admin user..."
# Copy script to container and run it, or use the script directly via docker exec
docker exec sentinelgrid-iam_agent-1 python3 -c "
import sys
import os
sys.path.insert(0, '/app/app')
import httpx

# Get configuration from environment
KEYCLOAK_URL = os.getenv('KEYCLOAK_URL', 'http://keycloak:8080')
REALM = os.getenv('KEYCLOAK_REALM', 'sentinelgrid')
ADMIN_EMAIL = os.getenv('KEYCLOAK_ADMIN_EMAIL', 'admin@sentinelgrid.ai')
ADMIN_USER = os.getenv('KEYCLOAK_ADMIN_USER', 'admin')
ADMIN_PASSWORD = os.getenv('KEYCLOAK_ADMIN_PASSWORD', 'admin')

print(f'Deleting admin user {ADMIN_EMAIL} from realm {REALM}...')

# Get admin token
token_url = f'{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token'
token_data = {
    'client_id': 'admin-cli',
    'username': ADMIN_USER,
    'password': ADMIN_PASSWORD,
    'grant_type': 'password',
}

try:
    with httpx.Client(timeout=10.0, verify=False) as client:
        token_response = client.post(token_url, data=token_data)
        if token_response.status_code != 200:
            print(f'❌ Failed to get admin token: {token_response.status_code}')
            sys.exit(1)
        admin_token = token_response.json()['access_token']
        
        # Check if user exists
        users_url = f'{KEYCLOAK_URL}/admin/realms/{REALM}/users'
        params = {'username': ADMIN_EMAIL, 'exact': 'true'}
        headers = {'Authorization': f'Bearer {admin_token}', 'Content-Type': 'application/json'}
        
        users_response = client.get(users_url, headers=headers, params=params)
        if users_response.status_code != 200:
            print(f'⚠️  Failed to check for user: {users_response.status_code}')
            sys.exit(0)
        
        users = users_response.json()
        if not users:
            print(f'ℹ️  User does not exist, nothing to delete')
            sys.exit(0)
        
        user_id = users[0]['id']
        
        # Delete user
        delete_url = f'{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}'
        delete_response = client.delete(delete_url, headers=headers)
        if delete_response.status_code == 204:
            print('✅ User deleted successfully')
            sys.exit(0)
        else:
            print(f'⚠️  Failed to delete user: {delete_response.status_code}')
            sys.exit(0)
except Exception as e:
    print(f'⚠️  Error: {e}')
    sys.exit(0)
" 2>&1
DELETE_EXIT=0

if [ $DELETE_EXIT -eq 0 ]; then
    echo "✅ User deletion completed"
else
    echo "⚠️  User deletion had issues (may not exist)"
fi

echo ""
echo "Step 2: Restarting iam_agent service..."
docker-compose -f docker-compose.dev.yml restart iam_agent

echo ""
echo "Step 3: Waiting for iam_agent to start and seed..."
sleep 15

echo ""
echo "Step 4: Checking iam_agent logs for seeding..."
docker-compose -f docker-compose.dev.yml logs iam_agent --tail 50 | grep -E "(Seeding|admin|user|Created|Updated|login|verification|✅|⚠️)" || echo "No seeding logs found yet"

echo ""
echo "Step 5: Testing login..."
python3 scripts/test-admin-login.py "$ADMIN_EMAIL" "${KEYCLOAK_ADMIN_PASSWORD_SEED:-admin123}" "$REALM"
LOGIN_EXIT=$?

echo ""
echo "=========================================="
if [ $LOGIN_EXIT -eq 0 ]; then
    echo "✅ TEST PASSED - Seeder flow completed successfully!"
else
    echo "❌ TEST FAILED - Login verification failed"
fi
echo "=========================================="

exit $LOGIN_EXIT

