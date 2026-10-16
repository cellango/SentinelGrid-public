# Entitlement Naming Convention

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Version:** 1.0  
**Date:** 2025-11-28  
**Status:** Design Complete

---

## Overview

This document defines the standardized naming convention for entitlements in SentinelGrid's multi-tenant architecture. Entitlements represent fine-grained permissions that grant users access to specific resources and actions within a tenant.

---

## Entitlement Format

### Standard Format

```
{resource_type}:{resource_id}:{action}@{tenant_id}
```

### Format Components

| Component | Description | Required | Example |
|-----------|-------------|----------|---------|
| `resource_type` | Type of resource (alerts, incidents, playbooks, etc.) | Yes | `alert`, `incident`, `playbook` |
| `resource_id` | Specific resource identifier or wildcard | Yes | `550e8400-...` or `*` |
| `action` | Operation allowed on resource | Yes | `read`, `write`, `delete`, `execute` |
| `tenant_id` | Tenant UUID for multi-tenant isolation | Yes | `6306bd5e-0bf2-4622-b789-ba0d18ae8003` |

---

## Resource Types

### Standard Resource Types

| Resource Type | Description | Common Actions |
|--------------|-------------|----------------|
| `alert` | Security alerts | `read`, `write`, `triage`, `acknowledge`, `close` |
| `incident` | Security incidents | `read`, `write`, `assign`, `escalate`, `resolve` |
| `playbook` | Automation playbooks | `read`, `write`, `execute`, `delete` |
| `integration` | External integrations | `read`, `configure`, `test`, `delete` |
| `user` | User accounts | `read`, `write`, `delete`, `manage_roles` |
| `tenant` | Tenant configuration | `read`, `write`, `manage` |
| `report` | Security reports | `read`, `write`, `generate`, `export` |
| `policy` | Security policies | `read`, `write`, `delete` |

---

## Actions

### Standard Actions

| Action | Description | Applies To |
|--------|-------------|------------|
| `read` | View resource | All resource types |
| `write` | Create or modify resource | All resource types |
| `delete` | Remove resource | Most resource types |
| `execute` | Run/execute resource | `playbook`, `integration` |
| `triage` | Triage/classify resource | `alert` |
| `assign` | Assign resource to user | `incident`, `alert` |
| `acknowledge` | Acknowledge resource | `alert` |
| `close` | Close resource | `alert`, `incident` |
| `escalate` | Escalate resource | `incident` |
| `resolve` | Resolve resource | `incident` |
| `configure` | Configure resource | `integration`, `tenant` |
| `test` | Test resource | `integration` |
| `generate` | Generate resource | `report` |
| `export` | Export resource | `report` |
| `manage_roles` | Manage user roles | `user` |

---

## Examples

### Alert Entitlements

```
# Read all alerts for tenant
alert:*:read@6306bd5e-0bf2-4622-b789-ba0d18ae8003

# Write specific alert
alert:550e8400-e29b-41d4-a716-446655440000:write@6306bd5e-0bf2-4622-b789-ba0d18ae8003

# Triage all alerts
alert:*:triage@6306bd5e-0bf2-4622-b789-ba0d18ae8003

# Acknowledge specific alert
alert:550e8400-e29b-41d4-a716-446655440000:acknowledge@6306bd5e-0bf2-4622-b789-ba0d18ae8003

# Close all alerts
alert:*:close@6306bd5e-0bf2-4622-b789-ba0d18ae8003
```

### Incident Entitlements

```
# Read all incidents
incident:*:read@6306bd5e-0bf2-4622-b789-ba0d18ae8003

# Write all incidents
incident:*:write@6306bd5e-0bf2-4622-b789-ba0d18ae8003

# Assign incidents
incident:*:assign@6306bd5e-0bf2-4622-b789-ba0d18ae8003

# Resolve specific incident
incident:123e4567-e89b-12d3-a456-426614174000:resolve@6306bd5e-0bf2-4622-b789-ba0d18ae8003
```

### Playbook Entitlements

```
# Read all playbooks
playbook:*:read@6306bd5e-0bf2-4622-b789-ba0d18ae8003

# Execute all playbooks
playbook:*:execute@6306bd5e-0bf2-4622-b789-ba0d18ae8003

# Write specific playbook
playbook:playbook-123:write@6306bd5e-0bf2-4622-b789-ba0d18ae8003

# Delete specific playbook
playbook:playbook-456:delete@6306bd5e-0bf2-4622-b789-ba0d18ae8003
```

### Integration Entitlements

```
# Read all integrations
integration:*:read@6306bd5e-0bf2-4622-b789-ba0d18ae8003

# Configure SIEM integration
integration:siem:configure@6306bd5e-0bf2-4622-b789-ba0d18ae8003

# Test specific integration
integration:siem:test@6306bd5e-0bf2-4622-b789-ba0d18ae8003
```

---

## Hierarchical Entitlements

Entitlements support hierarchical matching where more specific entitlements inherit from broader ones.

### Hierarchy Levels

1. **Tenant-level** (broadest)
   ```
   *:*:*@{tenant_id}
   ```
   Full access to all resources in tenant

2. **Resource-type-level**
   ```
   alert:*:*@{tenant_id}
   ```
   Full access to all alerts in tenant

3. **Resource-specific**
   ```
   alert:550e8400-...:*@{tenant_id}
   ```
   Full access to specific alert

4. **Action-specific**
   ```
   alert:550e8400-...:read@{tenant_id}
   ```
   Specific action on specific resource

### Matching Rules

When checking entitlements:
1. Check for exact match first
2. If not found, check parent resources (`resource_id = *`)
3. If not found, check parent resource type (`resource_type:*:*`)
4. If not found, check tenant-level (`*:*:*`)

**Example:**
User has: `alert:*:read@{tenant_id}`  
Checking: `alert:550e8400-...:read@{tenant_id}`  
Result: ✅ **Allowed** (matches parent)

---

## Role-to-Entitlement Mapping

Default entitlements granted by realm roles:

### TENANT_ADMIN

```
*:*:*@{tenant_id}
```

**Full access** to all resources and actions in the tenant.

### SOC_MANAGER

```
*:*:read@{tenant_id}
incident:*:write@{tenant_id}
incident:*:assign@{tenant_id}
incident:*:resolve@{tenant_id}
playbook:*:execute@{tenant_id}
integration:*:configure@{tenant_id}
report:*:generate@{tenant_id}
```

### SOC_ANALYST

```
alert:*:read@{tenant_id}
alert:*:triage@{tenant_id}
alert:*:acknowledge@{tenant_id}
incident:*:read@{tenant_id}
incident:*:write@{tenant_id}
playbook:*:read@{tenant_id}
report:*:read@{tenant_id}
```

### VIEW_ONLY

```
*:*:read@{tenant_id}
```

**Read-only access** to all resources in the tenant.

---

## Entitlement Validation

### Validation Rules

1. **Tenant Isolation:** Entitlements MUST include tenant_id
2. **Format Validation:** Must match standard format
3. **Resource Existence:** Resource must exist (for non-wildcard resource_id)
4. **Action Validity:** Action must be valid for resource type
5. **Hierarchy Check:** Check parent entitlements if exact match not found

### Validation Example

```python
def validate_entitlement(entitlement: str, tenant_id: str) -> bool:
    """
    Validate entitlement format and tenant isolation.
    
    Args:
        entitlement: Entitlement string to validate
        tenant_id: Expected tenant ID
    
    Returns:
        True if valid, False otherwise
    """
    # Parse entitlement
    if '@' not in entitlement:
        return False
    
    parts = entitlement.split('@')
    if len(parts) != 2:
        return False
    
    resource_part, entitlement_tenant_id = parts
    
    # Check tenant isolation
    if entitlement_tenant_id != tenant_id:
        return False  # Cross-tenant access denied
    
    # Validate resource part format
    resource_parts = resource_part.split(':')
    if len(resource_parts) != 3:
        return False
    
    resource_type, resource_id, action = resource_parts
    
    # Validate resource type
    valid_resource_types = ['alert', 'incident', 'playbook', 'integration', ...]
    if resource_type != '*' and resource_type not in valid_resource_types:
        return False
    
    # Validate action
    valid_actions = ['read', 'write', 'delete', 'execute', ...]
    if action not in valid_actions:
        return False
    
    return True
```

---

## Database Schema

### Entitlements Table

```sql
CREATE TABLE entitlements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    user_id UUID NOT NULL,
    entitlement TEXT NOT NULL,  -- Full entitlement string
    resource_type TEXT NOT NULL,
    resource_id TEXT,  -- NULL for wildcard '*'
    action TEXT NOT NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    granted_by UUID,  -- User who granted this entitlement
    expires_at TIMESTAMPTZ,  -- Optional expiration
    metadata JSONB,  -- Additional context (e.g., reason, conditions)
    
    -- Constraints
    UNIQUE(tenant_id, user_id, entitlement),
    CHECK (entitlement LIKE '%@' || tenant_id::text)
);

-- Indexes for performance
CREATE INDEX idx_entitlements_user_tenant ON entitlements(tenant_id, user_id);
CREATE INDEX idx_entitlements_resource ON entitlements(resource_type, resource_id) WHERE resource_id IS NOT NULL;
CREATE INDEX idx_entitlements_entitlement ON entitlements(entitlement);
CREATE INDEX idx_entitlements_expires ON entitlements(expires_at) WHERE expires_at IS NOT NULL;
```

---

## API Examples

### Grant Entitlement

```http
POST /internal/iam/entitlements/{tenant_id}/grant
Content-Type: application/json

{
    "user_id": "user-uuid",
    "entitlement": "alert:*:triage@6306bd5e-0bf2-4622-b789-ba0d18ae8003",
    "expires_at": "2025-12-31T23:59:59Z",  // Optional
    "metadata": {
        "reason": "Temporary escalation for incident response",
        "granted_by_role": "TENANT_ADMIN"
    }
}
```

### Check Entitlement

```http
POST /internal/iam/entitlements/{tenant_id}/check
Content-Type: application/json

{
    "user_id": "user-uuid",
    "resource_type": "alert",
    "resource_id": "550e8400-e29b-41d4-a716-446655440000",
    "action": "triage"
}
```

**Response:**
```json
{
    "authorized": true,
    "matched_entitlement": "alert:*:triage@6306bd5e-0bf2-4622-b789-ba0d18ae8003",
    "match_type": "hierarchical"  // or "exact"
}
```

---

## Best Practices

1. **Always include tenant_id** - Never grant cross-tenant entitlements
2. **Use wildcards judiciously** - Prefer specific resource_ids when possible
3. **Regular audits** - Review and revoke unused entitlements
4. **Time-limited entitlements** - Use `expires_at` for temporary access
5. **Document reasons** - Use `metadata` to track why entitlements were granted
6. **Principle of least privilege** - Grant minimal required entitlements

---

## Migration from Roles

When migrating from role-based to entitlement-based access:

1. Map existing roles to default entitlements
2. Grant default entitlements to users based on their roles
3. Allow fine-grained entitlements to override defaults
4. Gradually transition to entitlement-based checks

---

**Related Documents:**
- `ARCHITECTURE_AI_IAM_AGENTS.md` - Agent architecture
- `ARCHITECTURE_AUTH_AUTHORIZATION.md` - Overall auth architecture

