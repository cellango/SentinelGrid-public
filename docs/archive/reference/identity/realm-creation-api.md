# Realm Creation API Documentation

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Version:** 1.0  
**Last Updated:** 2025-01-28  
**Base URL:** `http://localhost:8000` (IAM Agent service)

---

## Overview

The Realm Creation API provides a centralized endpoint for creating Keycloak realms with all required configuration, including:

- User Profile configuration (CRITICAL for Keycloak v25+)
- Standard clients (web, api, iam-agent)
- Standard roles (TENANT_ADMIN, SOC_MANAGER, SOC_ANALYST, VIEW_ONLY)
- Protocol mappers for `tenant_id` claim
- Naming convention enforcement

**CRITICAL:** All realm creation MUST go through this API. See [CRITICAL_TECHNICAL_REQUIREMENTS.md](../platform/critical-technical-requirements.md) for details.

---

## Endpoints

### Create Realm

Create a new Keycloak realm with all standard configuration.

**Endpoint:** `POST /api/v1/realms`

**Authorization:** Requires platform admin privileges (PLATFORM_ADMIN role in sg-admin realm)

**Request Body:**

```json
{
  "realm_name": "sg-mt-us-1",
  "realm_type": "multi_tenant",
  "display_name": "SentinelGrid Multi-Tenant (US Shard 1)",
  "region": "us",
  "shard_number": 1
}
```

**Request Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `realm_name` | string | Yes | Name of the realm (must follow naming conventions) |
| `realm_type` | enum | Yes | Type of realm: `platform_admin`, `multi_tenant`, `dedicated_customer`, `demo` |
| `display_name` | string | No | Display name for the realm (defaults to `realm_name`) |
| `region` | string | No | Region code for multi-tenant realms (e.g., `us`, `eu`) |
| `shard_number` | integer | No | Shard number for multi-tenant realms (e.g., `1`, `2`) |
| `customer_slug` | string | No | Customer slug for dedicated customer realms |

**Response (201 Created):**

```json
{
  "realm_name": "sg-mt-us-1",
  "keycloak_realm_id": "${EXAMPLE_VALUE}",
  "status": "created",
  "user_profile_configured": true
}
```

**Response (200 OK - Realm Already Exists):**

```json
{
  "realm_name": "sg-mt-us-1",
  "keycloak_realm_id": "${EXAMPLE_VALUE}",
  "status": "exists",
  "user_profile_configured": true
}
```

**Response Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `realm_name` | string | Name of the realm |
| `keycloak_realm_id` | string | Keycloak internal realm ID |
| `status` | string | `"created"` if new realm, `"exists"` if realm already existed |
| `user_profile_configured` | boolean | Whether User Profile was configured with `tenant_id` attribute |

**Error Responses:**

| Status Code | Description | Example |
|-------------|-------------|---------|
| 400 Bad Request | Invalid request (naming convention violation, missing required fields) | `{"detail": "Invalid realm name: Multi-tenant realm name must be 'sg-mt-us-1', got 'invalid-name'"}` |
| 401 Unauthorized | Missing or invalid authentication | `{"detail": "Not authenticated"}` |
| 403 Forbidden | Insufficient permissions | `{"detail": "Requires platform admin privileges"}` |
| 409 Conflict | Realm name conflict (should not occur with proper validation) | `{"detail": "Realm 'sg-mt-us-1' already exists"}` |
| 500 Internal Server Error | Server error | `{"detail": "Failed to create realm: ..."}` |
| 503 Service Unavailable | Keycloak admin service unavailable | `{"detail": "Keycloak admin service unavailable"}` |

---

### Get Realm Status

Get the status of a realm, including User Profile configuration.

**Endpoint:** `GET /api/v1/realms/{realm_name}/status`

**Authorization:** Requires platform admin privileges

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `realm_name` | string | Name of the realm |

**Response (200 OK):**

```json
{
  "realm_name": "sg-mt-us-1",
  "exists": true,
  "user_profile_configured": true,
  "keycloak_realm_id": "${EXAMPLE_VALUE}"
}
```

**Response Schema:**

| Field | Type | Description |
|-------|------|-------------|
| `realm_name` | string | Name of the realm |
| `exists` | boolean | Whether the realm exists in Keycloak |
| `user_profile_configured` | boolean | Whether User Profile is configured with `tenant_id` attribute |
| `keycloak_realm_id` | string | Keycloak internal realm ID (null if realm doesn't exist) |

**Error Responses:**

| Status Code | Description |
|-------------|-------------|
| 401 Unauthorized | Missing or invalid authentication |
| 403 Forbidden | Insufficient permissions |
| 500 Internal Server Error | Server error |

---

## Realm Types

### Platform Admin

**Type:** `platform_admin`  
**Naming Convention:** Must be exactly `sg-admin`

**Example Request:**

```json
{
  "realm_name": "sg-admin",
  "realm_type": "platform_admin",
  "display_name": "SentinelGrid Platform Admin"
}
```

**Creates:**
- Realm: `sg-admin`
- Clients: `sg-admin-admin`, `sentinelgrid-iam-agent`
- Roles: `PLATFORM_ADMIN`, `SUPPORT_ENGINEER`, `SOC_OPERATOR`
- User Profile: Configured with `tenant_id` attribute

---

### Multi-Tenant

**Type:** `multi_tenant`  
**Naming Convention:** `sg-mt-{region}-{shard}` (e.g., `sg-mt-us-1`)

**Example Request:**

```json
{
  "realm_name": "sg-mt-us-1",
  "realm_type": "multi_tenant",
  "display_name": "SentinelGrid Multi-Tenant (US Shard 1)",
  "region": "us",
  "shard_number": 1
}
```

**Required Fields:**
- `region`: Region code (e.g., `us`, `eu`, `ap`)
- `shard_number`: Shard number (e.g., `1`, `2`, `3`)

**Creates:**
- Realm: `sg-mt-{region}-{shard}`
- Clients: `{realm_name}-web`, `{realm_name}-api`, `sentinelgrid-iam-agent`
- Roles: `TENANT_ADMIN`, `SOC_MANAGER`, `SOC_ANALYST`, `VIEW_ONLY`
- User Profile: Configured with `tenant_id` attribute
- Protocol Mappers: `tenant-id-mapper` for `tenant_id` claim

---

### Dedicated Customer

**Type:** `dedicated_customer`  
**Naming Convention:** `{customer-slug}` (e.g., `agribotsai`)

**Example Request:**

```json
{
  "realm_name": "agribotsai",
  "realm_type": "dedicated_customer",
  "display_name": "AgribotsAI",
  "customer_slug": "agribotsai"
}
```

**Required Fields:**
- `customer_slug`: Customer slug (must match `realm_name`)

**Validation:**
- Slug must be lowercase alphanumeric with hyphens/underscores
- Max 50 characters
- Must match `realm_name`

**Creates:**
- Realm: `{customer-slug}`
- Clients: `{realm_name}-web`, `{realm_name}-api`, `sentinelgrid-iam-agent`
- Roles: `TENANT_ADMIN`, `SOC_MANAGER`, `SOC_ANALYST`, `VIEW_ONLY`
- User Profile: Configured with `tenant_id` attribute
- Protocol Mappers: `tenant-id-mapper` for `tenant_id` claim

---

### Demo

**Type:** `demo`  
**Naming Convention:** Must be exactly `demo`

**Example Request:**

```json
{
  "realm_name": "demo",
  "realm_type": "demo",
  "display_name": "Demo Company"
}
```

**Creates:**
- Realm: `demo`
- Clients: `demo-web`, `demo-api`, `sentinelgrid-iam-agent`
- Roles: `TENANT_ADMIN`, `SOC_MANAGER`, `SOC_ANALYST`, `VIEW_ONLY`
- User Profile: Configured with `tenant_id` attribute
- Protocol Mappers: `tenant-id-mapper` for `tenant_id` claim

---

## Examples

### Create Multi-Tenant Realm

```bash
curl -X POST http://localhost:8000/api/v1/realms \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <platform-admin-token>" \
  -d '{
    "realm_name": "sg-mt-us-1",
    "realm_type": "multi_tenant",
    "display_name": "SentinelGrid Multi-Tenant (US Shard 1)",
    "region": "us",
    "shard_number": 1
  }'
```

### Check Realm Status

```bash
curl -X GET http://localhost:8000/api/v1/realms/sg-mt-us-1/status \
  -H "Authorization: Bearer <platform-admin-token>"
```

### Create Dedicated Customer Realm

```bash
curl -X POST http://localhost:8000/api/v1/realms \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <platform-admin-token>" \
  -d '{
    "realm_name": "agribotsai",
    "realm_type": "dedicated_customer",
    "display_name": "AgribotsAI",
    "customer_slug": "agribotsai"
  }'
```

---

## Error Handling

### Naming Convention Violation

**Request:**
```json
{
  "realm_name": "invalid-name",
  "realm_type": "multi_tenant",
  "region": "us",
  "shard_number": 1
}
```

**Response (400 Bad Request):**
```json
{
  "detail": "Invalid realm name: Multi-tenant realm name must be 'sg-mt-us-1', got 'invalid-name'"
}
```

### Missing Required Fields

**Request:**
```json
{
  "realm_name": "sg-mt-us-1",
  "realm_type": "multi_tenant"
}
```

**Response (400 Bad Request):**
```json
{
  "detail": "Invalid realm name: Multi-tenant realm requires region and shard_number"
}
```

### Realm Already Exists

**Request:**
```json
{
  "realm_name": "sg-mt-us-1",
  "realm_type": "multi_tenant",
  "region": "us",
  "shard_number": 1
}
```

**Response (200 OK):**
```json
{
  "realm_name": "sg-mt-us-1",
  "keycloak_realm_id": "${EXAMPLE_VALUE}",
  "status": "exists",
  "user_profile_configured": true
}
```

**Note:** The API is idempotent - creating an existing realm returns success with `status: "exists"`.

---

## Implementation Details

### Automatic Configuration

When a realm is created, the API automatically:

1. **Validates** realm name against naming conventions
2. **Creates** realm in Keycloak
3. **Configures** User Profile with `tenant_id` attribute (CRITICAL)
4. **Creates** standard clients (web, api, iam-agent)
5. **Creates** standard roles (TENANT_ADMIN, SOC_MANAGER, SOC_ANALYST, VIEW_ONLY)
6. **Creates** protocol mappers for `tenant_id` claim

### User Profile Configuration

The User Profile is configured with:

```json
{
  "attributes": [
    {
      "name": "tenant_id",
      "displayName": "Tenant ID",
      "validations": {},
      "annotations": {
        "description": "Universal tenant isolation boundary for multi-tenancy"
      },
      "permissions": {
        "view": ["admin", "user"],
        "edit": ["admin"]
      },
      "multivalued": false
    }
  ]
}
```

**CRITICAL:** This is a Keycloak v25+ requirement. Without this configuration, custom attributes will NOT persist.

### Idempotency

The API is idempotent:
- Creating an existing realm returns success with `status: "exists"`
- User Profile is verified and configured if missing
- Standard clients, roles, and mappers are created if missing

---

## Related Documentation

- [Critical Technical Requirements](../platform/critical-technical-requirements.md)
- [Keycloak User Profile Configuration](../../../../scripts/configure_user_profile.sh)
- [Multi-Tenant Architecture](../../README.md#retired-references)

---

## Support

For questions or issues:

1. Check this documentation
2. Review [Critical Technical Requirements](../platform/critical-technical-requirements.md)
3. Check implementation in `backend/agents/iam_agent/app/services/realm_creation_service.py`
4. Contact the platform team

