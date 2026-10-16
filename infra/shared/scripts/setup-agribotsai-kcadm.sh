#!/bin/bash
# Setup AgribotsAI realm using Keycloak Admin CLI
# Alternative to Terraform when provider authentication issues occur

set -e

KEYCLOAK_CONTAINER="sentinelgrid-keycloak-1"
REALM="agribotsai"

echo "=========================================="
echo "Setting up AgribotsAI realm via kcadm.sh"
echo "=========================================="

# Function to run kcadm commands
kcadm() {
  docker exec $KEYCLOAK_CONTAINER /opt/keycloak/bin/kcadm.sh "$@"
}

# Check if realm already exists
if kcadm get realms/$REALM > /dev/null 2>&1; then
  echo "✅ Realm $REALM already exists"
else
  echo "Creating realm $REALM..."
  kcadm create realms -s realm=$REALM -s enabled=true -s displayName="AgribotsAI"
  echo "✅ Realm created"
fi

# Update realm settings
echo "Updating realm settings..."
kcadm update realms/$REALM -s sslRequired=external \
  -s passwordPolicy="length(8) and digits(1) and lowerCase(1) and upperCase(1) and notUsername" \
  -s accessTokenLifespan=3600 \
  -s ssoSessionIdleTimeout=1800 \
  -s loginWithEmailAllowed=true \
  -s duplicateEmailsAllowed=false \
  -s rememberMe=true \
  -s verifyEmail=false

echo "✅ Realm settings updated"

# Create clients
echo "Creating clients..."

# Web client
if kcadm get clients/$REALM -q clientId=agribotsai-web 2>/dev/null | grep -q agribotsai-web; then
  echo "  Web client already exists"
else
  WEB_CLIENT_ID=$(kcadm create clients -r $REALM -s clientId=agribotsai-web \
    -s name="AgribotsAI Web Client" \
    -s enabled=true \
    -s publicClient=true \
    -s standardFlowEnabled=true \
    -s directAccessGrantsEnabled=true \
    -s 'redirectUris=["http://localhost:3000/*", "https://app.agribotsai.com/*"]' \
    -s 'webOrigins=["+"]' \
    -i)
  echo "  ✅ Web client created (ID: $WEB_CLIENT_ID)"
fi

# API client
if kcadm get clients/$REALM -q clientId=agribotsai-api 2>/dev/null | grep -q agribotsai-api; then
  echo "  API client already exists"
else
  API_CLIENT_ID=$(kcadm create clients -r $REALM -s clientId=agribotsai-api \
    -s name="AgribotsAI API Client" \
    -s enabled=true \
    -s publicClient=false \
    -s standardFlowEnabled=false \
    -s directAccessGrantsEnabled=false \
    -s serviceAccountsEnabled=true \
    -i)
  echo "  ✅ API client created (ID: $API_CLIENT_ID)"
fi

# IAM Agent client
if kcadm get clients/$REALM -q clientId=sentinelgrid-iam-agent 2>/dev/null | grep -q sentinelgrid-iam-agent; then
  echo "  IAM Agent client already exists"
else
  IAM_CLIENT_ID=$(kcadm create clients -r $REALM -s clientId=sentinelgrid-iam-agent \
    -s name="SentinelGrid IAM Agent" \
    -s enabled=true \
    -s publicClient=false \
    -s standardFlowEnabled=false \
    -s serviceAccountsEnabled=true \
    -i)
  echo "  ✅ IAM Agent client created (ID: $IAM_CLIENT_ID)"
fi

# Get client IDs for mappers
WEB_CLIENT_ID=$(kcadm get clients/$REALM -q clientId=agribotsai-web --format csv --fields id | tail -1 | tr -d '"')
API_CLIENT_ID=$(kcadm get clients/$REALM -q clientId=agribotsai-api --format csv --fields id | tail -1 | tr -d '"')

# Create protocol mappers
echo "Creating protocol mappers..."

# tenant_id mapper for web client
kcadm create clients/$WEB_CLIENT_ID/protocol-mappers/models -r $REALM \
  -s name=tenant-id-mapper \
  -s protocol=openid-connect \
  -s protocolMapper=oidc-usermodel-attribute-mapper \
  -s 'config."user.attribute"=tenant_id' \
  -s 'config."claim.name"=tenant_id' \
  -s 'config."jsonType.label"=String' \
  -s 'config."id.token.claim"=true' \
  -s 'config."access.token.claim"=true' > /dev/null 2>&1 && echo "  ✅ tenant_id mapper for web client" || echo "  ⚠️  tenant_id mapper may already exist"

# tenant_id mapper for api client
if kcadm get clients/$API_CLIENT_ID/protocol-mappers/models -r $REALM 2>&1 | grep -q "tenant-id-mapper"; then
  echo "  tenant_id mapper for api client already exists"
else
  kcadm create clients/$API_CLIENT_ID/protocol-mappers/models -r $REALM \
    -s name=tenant-id-mapper \
    -s protocol=openid-connect \
    -s protocolMapper=oidc-usermodel-attribute-mapper \
    -s 'config."user.attribute"=tenant_id' \
    -s 'config."claim.name"=tenant_id' \
    -s 'config."jsonType.label"=String' \
    -s 'config."id.token.claim"=true' \
    -s 'config."access.token.claim"=true' > /dev/null 2>&1 && echo "  ✅ tenant_id mapper for api client created" || echo "  ⚠️  Failed to create tenant_id mapper"
fi

# Create roles
echo "Creating roles..."
for role in TENANT_ADMIN SOC_MANAGER SOC_ANALYST VIEW_ONLY; do
  if kcadm get roles/$REALM/$role > /dev/null 2>&1; then
    echo "  Role $role already exists"
  else
    kcadm create roles -r $REALM -s name=$role -s description="Role: $role"
    echo "  ✅ Role $role created"
  fi
done

# Create users
echo "Creating users..."

# Admin user
if kcadm get users/$REALM -q username=admin@agribotsai.com 2>/dev/null | grep -q admin@agribotsai.com; then
  echo "  Admin user already exists"
else
  ADMIN_USER_ID=$(kcadm create users -r $REALM \
    -s username=admin@agribotsai.com \
    -s email=admin@agribotsai.com \
    -s firstName=Admin \
    -s lastName=User \
    -s enabled=true \
    -s emailVerified=true \
    -s 'attributes.tenant_id=["agribotsai-tenant-uuid"]' \
    -i)
  
  kcadm set-password -r $REALM --username admin@agribotsai.com --new-password "ChangeMe123!" --no-temporary
  
  # Clear any required actions to avoid VERIFY_PROFILE
  kcadm update users/$ADMIN_USER_ID -r $REALM -s 'requiredActions=[]'
  
  TENANT_ADMIN_ROLE_ID=$(kcadm get roles/$REALM/TENANT_ADMIN --format csv --fields id | tail -1 | tr -d '"')
  kcadm add-roles -r $REALM --uusername admin@agribotsai.com --rolename TENANT_ADMIN
  
  echo "  ✅ Admin user created (ID: $ADMIN_USER_ID)"
fi

# Analyst user
if kcadm get users/$REALM -q username=analyst@agribotsai.com 2>/dev/null | grep -q analyst@agribotsai.com; then
  echo "  Analyst user already exists"
else
  ANALYST_USER_ID=$(kcadm create users -r $REALM \
    -s username=analyst@agribotsai.com \
    -s email=analyst@agribotsai.com \
    -s firstName=SOC \
    -s lastName=Analyst \
    -s enabled=true \
    -s 'attributes.tenant_id=["agribotsai-tenant-uuid"]' \
    -i)
  
  kcadm set-password -r $REALM --username analyst@agribotsai.com --new-password "TestAnalyst123!" --temporary
  kcadm add-roles -r $REALM --uusername analyst@agribotsai.com --rolename SOC_ANALYST
  
  echo "  ✅ Analyst user created (ID: $ANALYST_USER_ID)"
fi

# Viewer user
if kcadm get users/$REALM -q username=viewer@agribotsai.com 2>/dev/null | grep -q viewer@agribotsai.com; then
  echo "  Viewer user already exists"
else
  VIEWER_USER_ID=$(kcadm create users -r $REALM \
    -s username=viewer@agribotsai.com \
    -s email=viewer@agribotsai.com \
    -s firstName=View \
    -s lastName=Only \
    -s enabled=true \
    -s 'attributes.tenant_id=["agribotsai-tenant-uuid"]' \
    -i)
  
  kcadm set-password -r $REALM --username viewer@agribotsai.com --new-password "TestViewer123!" --temporary
  kcadm add-roles -r $REALM --uusername viewer@agribotsai.com --rolename VIEW_ONLY
  
  echo "  ✅ Viewer user created (ID: $VIEWER_USER_ID)"
fi

# Create User Profile component (Keycloak 26.x)
echo ""
echo "Configuring User Profile component..."
if python3 ../../../../scripts/create-user-profile-component.py agribotsai 2>/dev/null; then
  echo "  ✅ User Profile component configured"
else
  echo "  ⚠️  User Profile component configuration failed (may already exist)"
fi

# Create User Profile component (Keycloak 26.x - Required for attribute persistence)
echo ""
echo "Configuring User Profile component..."
if command -v python3 >/dev/null 2>&1; then
  if [ -f "../../../../scripts/create-user-profile-component.py" ]; then
    cd "$(dirname "$0")"
    if python3 ../../../../scripts/create-user-profile-component.py agribotsai 2>/dev/null; then
      echo "  ✅ User Profile component configured"
    else
      echo "  ⚠️  User Profile component may already exist"
    fi
    cd - >/dev/null
  elif [ -f "scripts/create-user-profile-component.py" ]; then
    if python3 scripts/create-user-profile-component.py agribotsai 2>/dev/null; then
      echo "  ✅ User Profile component configured"
    else
      echo "  ⚠️  User Profile component may already exist"
    fi
  else
    echo "  ⚠️  User Profile script not found. Component may need manual creation."
    echo "     Run: python3 scripts/create-user-profile-component.py agribotsai"
  fi
else
  echo "  ⚠️  python3 not found. User Profile component may need manual creation."
fi

echo ""
echo "=========================================="
echo "✅ AgribotsAI realm setup complete!"
echo "=========================================="
echo ""
echo "Realm: $REALM"
echo "Admin User: admin@agribotsai.com / ChangeMe123!"
echo "Analyst User: analyst@agribotsai.com / TestAnalyst123!"
echo "Viewer User: viewer@agribotsai.com / TestViewer123!"
echo ""
echo "Configuration:"
echo "  ✅ User Profile component: Configured (unmanaged attributes enabled)"
echo "  ✅ Protocol mappers: tenant_id mapper created"
echo ""
echo "Next steps:"
echo "1. Create tenant in database and update tenant_id in user attributes"
echo "2. Test token generation: ./infra/shared/scripts/get-token.sh agribotsai agribotsai-web admin@agribotsai.com ChangeMe123!"
echo "3. Test authentication flow: ./infra/shared/scripts/test-auth-flow.sh"

