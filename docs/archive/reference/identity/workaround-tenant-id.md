# Tenant ID Workaround - Database Lookup

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Status:** Active Workaround  
**Date:** 2025-11-28

---

## Problem

Keycloak v25.0 user attribute persistence is not working via `kcadm.sh` or Admin REST API. The `tenant_id` attribute cannot be set on users, blocking multi-tenant isolation via token claims.

---

## Workaround: Database Lookup

Instead of reading `tenant_id` from JWT token claims, we'll look it up from our PostgreSQL database.

### Implementation

#### 1. Create User-Tenant Mapping Table

```sql
-- Add user_tenants table for explicit user-tenant mapping
CREATE TABLE IF NOT EXISTS user_tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,  -- Keycloak user ID (sub claim)
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, tenant_id)
);

CREATE INDEX idx_user_tenants_user ON user_tenants(user_id);
CREATE INDEX idx_user_tenants_tenant ON user_tenants(tenant_id);
```

#### 2. Update Security Library

```python
# backend/libs/sg_core/security.py

from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.user_tenants import UserTenant

def get_tenant_id_from_token_or_db(
    token_payload: dict,
    db: Session
) -> Optional[str]:
    """
    Get tenant_id from token claim (if present) or database lookup.
    
    This is a workaround for Keycloak attribute persistence issues.
    """
    # Try token claim first (will be None until Keycloak issue is fixed)
    tenant_id = token_payload.get("tenant_id")
    
    if tenant_id:
        return tenant_id
    
    # Fallback to database lookup
    user_id = token_payload.get("sub")
    if not user_id:
        return None
    
    # Query database for user-tenant mapping
    stmt = select(UserTenant).where(UserTenant.user_id == user_id)
    user_tenant = db.execute(stmt).scalar_one_or_none()
    
    if user_tenant:
        return str(user_tenant.tenant_id)
    
    return None
```

#### 3. Update IAM Agent Token Validator

```python
# backend/services/iam_agent/app/services/token_validator.py

def validate_token(self, token: str, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Validate token and extract tenant_id from token or database.
    """
    # ... existing validation code ...
    
    # Extract tenant_id
    tenant_id = payload.get("tenant_id")
    
    # Workaround: If tenant_id not in token, try database lookup
    if not tenant_id and db:
        from app.models.user_tenants import UserTenant
        from sqlalchemy import select
        
        user_id = payload.get("sub")
        if user_id:
            stmt = select(UserTenant).where(UserTenant.user_id == user_id)
            user_tenant = db.execute(stmt).scalar_one_or_none()
            if user_tenant:
                tenant_id = str(user_tenant.tenant_id)
    
    return {
        "valid": True,
        "tenant_id": tenant_id,
        # ... other fields ...
    }
```

---

## Migration Strategy

### Phase 1: Dual Support (Current)
- Check token claim first
- Fall back to database if not found
- Allows gradual migration

### Phase 2: Database Primary (Until Keycloak Fixed)
- Make database lookup primary
- Log when token claim is missing
- Monitor for Keycloak fix

### Phase 3: Token-Only (After Keycloak Fix)
- Remove database lookup
- Use token claim exclusively
- More efficient

---

## Pros and Cons

### Pros
- ✅ **Unblocks development** - Can continue with multi-tenant isolation
- ✅ **Reliable** - Database is our source of truth
- ✅ **Auditable** - Can track user-tenant assignments
- ✅ **Flexible** - Can assign users to multiple tenants if needed

### Cons
- ⚠️ **Performance** - Requires database query per request
- ⚠️ **Complexity** - Two sources of truth (database + Keycloak)
- ⚠️ **Cache needed** - Should cache user-tenant mappings
- ⚠️ **Not standard** - JWT tokens typically contain all needed claims

---

## Caching Strategy

To mitigate performance impact, cache user-tenant mappings:

```python
from cachetools import TTLCache

# Cache user_id -> tenant_id for 5 minutes
user_tenant_cache = TTLCache(maxsize=10000, ttl=300)

def get_tenant_id_cached(user_id: str, db: Session) -> Optional[str]:
    # Check cache first
    if user_id in user_tenant_cache:
        return user_tenant_cache[user_id]
    
    # Query database
    tenant_id = get_tenant_id_from_db(user_id, db)
    
    # Cache result
    if tenant_id:
        user_tenant_cache[user_id] = tenant_id
    
    return tenant_id
```

---

## Management Scripts

### Assign User to Tenant

```bash
# scripts/assign-user-to-tenant.sh
USER_ID=$1
TENANT_UUID=$2

psql -U sg -d sg <<EOF
INSERT INTO user_tenants (user_id, tenant_id)
VALUES ('$USER_ID', '$TENANT_UUID'::uuid)
ON CONFLICT (user_id, tenant_id) DO NOTHING;
EOF
```

### Get User's Tenant

```bash
# scripts/get-user-tenant.sh
USER_ID=$1

psql -U sg -d sg -t -c "
SELECT t.name, t.slug, t.id::text
FROM user_tenants ut
JOIN tenants t ON ut.tenant_id = t.id
WHERE ut.user_id = '$USER_ID';
"
```

---

## Next Steps

1. ✅ Create `user_tenants` table
2. ✅ Update security library with database lookup
3. ✅ Add caching layer
4. ✅ Update API Gateway to use new function
5. ⏳ Create management scripts
6. ⏳ Update documentation

---

**Related:**
- `TENANT_ID_FIX_IN_PROGRESS.md` - Ongoing investigation
- `TENANT_ID_DEBUG_SUMMARY.md` - Debug notes

