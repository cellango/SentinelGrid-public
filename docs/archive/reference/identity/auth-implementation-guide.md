# Authentication & Authorization - Quick Implementation Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This is a quick-start guide for implementing the Auth/Authz architecture. See `ARCHITECTURE_AUTH_AUTHORIZATION.md` for full details.

## Quick Start Checklist

### 1. Update Keycloak in Docker Compose
- [ ] Update to Keycloak v25.x
- [ ] Add PostgreSQL for Keycloak DB
- [ ] Configure realm import
- [ ] Set environment variables

### 2. Implement IAM Agent Service
- [ ] Create Keycloak Admin client
- [ ] Implement token validation
- [ ] Add user management endpoints
- [ ] Add role management endpoints
- [ ] Add IAM findings detection

### 3. Update API Gateway
- [ ] Use IAM Agent for token validation
- [ ] Extract tenant_id from token
- [ ] Enforce RBAC

### 4. Update Security Library
- [ ] Remove stub token validation
- [ ] Call IAM Agent for validation
- [ ] Cache public keys (JWKS)

### 5. (Optional) MCP Integration
- [ ] Install MCP SDK
- [ ] Create MCP server in IAM Agent
- [ ] Expose Keycloak data via MCP
- [ ] Connect Model Gateway to MCP

## Implementation Order

### Day 1: Keycloak Setup
```bash
# Update docker-compose.yml
# Add Keycloak PostgreSQL
# Configure realm
```

### Day 2: IAM Agent Core
```bash
# Install python-keycloak
# Create KeycloakClient
# Implement token validation
# Test with real tokens
```

### Day 3: API Integration
```bash
# Update API Gateway
# Update security.py
# Test auth flow end-to-end
```

### Day 4: User Management
```bash
# Add user CRUD endpoints
# Add role management
# Test with frontend
```

### Day 5: MCP (Optional)
```bash
# Install MCP SDK
# Create MCP server
# Test with Model Gateway
```

## Key Files to Create/Update

### New Files
```
backend/services/iam_agent/
├── app/
│   ├── api/
│   │   ├── auth.py          # Token validation endpoints
│   │   ├── users.py         # User management
│   │   └── roles.py         # Role management
│   ├── services/
│   │   ├── keycloak_client.py
│   │   └── token_validator.py
│   └── models/
│       └── identity.py

infra/keycloak/
├── realm-export.json        # Realm configuration
└── docker-compose.keycloak.yml
```

### Files to Update
```
docker-compose.dev.yml       # Keycloak config
backend/libs/sg_core/security.py  # Use IAM Agent
backend/services/api_gateway/app/main.py  # Auth middleware
```

## Testing Checklist

- [ ] Keycloak starts successfully
- [ ] Can create realm and clients via admin console
- [ ] IAM Agent can connect to Keycloak
- [ ] Token validation works
- [ ] Frontend can login and get tokens
- [ ] API Gateway validates tokens correctly
- [ ] Tenant isolation works
- [ ] Role-based access control works
- [ ] MCP server exposes data (if implemented)

## Common Issues & Solutions

**Issue:** Token validation fails
- Check JWKS endpoint is accessible
- Verify realm name matches
- Check token issuer matches

**Issue:** tenant_id not in token
- Configure protocol mapper in Keycloak
- Set user attribute `tenant_id`
- Restart Keycloak

**Issue:** IAM Agent can't connect
- Check Keycloak admin credentials
- Verify network connectivity
- Check service account client exists

## Next Steps After Auth is Working

1. Add identity sync to database
2. Implement IAM findings detection
3. Add identity analytics
4. Connect MCP for AI queries
5. Add audit logging

