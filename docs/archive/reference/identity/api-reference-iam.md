# IAM API Reference - Complete

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Version:** 1.0  
**Last Updated:** December 3, 2025  
**Base URL:** `http://api.sentinelgrid.ai`

---

## Overview

This document provides complete API reference for SentinelGrid's IAM (Identity and Access Management) system.

**Base Services:**
- **IAM Agent:** Port 8000 - Authentication, users, roles, MFA
- **Entitlement Agent:** Port 8001 - Authorization, entitlements

**Authentication:** All endpoints (except public auth) require Bearer token in Authorization header.

**Tenant Isolation:** All APIs enforce strict tenant isolation based on JWT token's tenant_id.

---

## Authentication APIs (Public)

### POST /api/v1/auth/signup

Create new customer account.

**Request:**
```json
{
  "company_name": "string",
  "email": "string (email)",
  "password": "string (min 8 chars)",
  "first_name": "string",
  "last_name": "string",
  "employee_count": number
}
```

**Response (200):**
```json
{
  "success": true,
  "tenant_id": "uuid",
  "realm": "sentinelgrid",
  "user_id": "uuid",
  "message": "Account created successfully"
}
```

---

### POST /api/v1/auth/login

Authenticate user and get JWT token.

**Request:**
```json
{
  "email": "string",
  "password": "string"
}
```

**Response (200):**
```json
{
  "access_token": "jwt-token",
  "refresh_token": "jwt-token",
  "expires_in": 3600,
  "token_type": "Bearer",
  "user": {
    "id": "uuid",
    "email": "string",
    "tenant_id": "uuid",
    "roles": ["TENANT_ADMIN"]
  }
}
```

---

### POST /api/v1/auth/refresh

Refresh access token.

**Request:**
```json
{
  "refresh_token": "string"
}
```

**Response (200):** Same as login response

---

### GET /api/v1/auth/me

Get current user information.

**Headers:** `Authorization: Bearer {token}`

**Response (200):**
```json
{
  "id": "uuid",
  "email": "string",
  "tenant_id": "uuid",
  "roles": ["TENANT_ADMIN"],
  "realm": "sentinelgrid"
}
```

---

## User Management APIs

**Base:** `/api/v1/users`  
**Auth Required:** Yes  
**Tenant Isolation:** Enforced

### GET /api/v1/users

List users in tenant with pagination.

**Query Parameters:**
- `page` (int, default: 1) - Page number
- `limit` (int, default: 50, max: 100) - Items per page
- `search` (string, optional) - Search query
- `role` (string, optional) - Filter by role
- `enabled` (boolean, optional) - Filter by status

**Response (200):**
```json
{
  "items": [
    {
      "id": "uuid",
      "username": "string",
      "email": "string",
      "firstName": "string",
      "lastName": "string",
      "enabled": boolean,
      "emailVerified": boolean,
      "tenant_id": "uuid",
      "customer_id": "uuid",
      "createdTimestamp": number
    }
  ],
  "total": number,
  "page": number,
  "limit": number,
  "pages": number
}
```

---

### GET /api/v1/users/search

Search users by email, name, or username.

**Query Parameters:**
- `q` (string, required) - Search query
- `page` (int) - Page number
- `limit` (int) - Items per page

**Response:** Same as list users

---

### GET /api/v1/users/{user_id}

Get user details.

**Response (200):** Single user object

**Errors:**
- 404: User not found (or belongs to different tenant)

---

### PUT /api/v1/users/{user_id}

Update user information.

**Request:**
```json
{
  "firstName": "string (optional)",
  "lastName": "string (optional)",
  "email": "string (optional)",
  "enabled": boolean (optional)
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "User updated successfully"
}
```

---

### DELETE /api/v1/users/{user_id}

Delete user (soft delete - disables account).

**Response (200):**
```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

---

### POST /api/v1/users/{user_id}/deactivate

Deactivate user account.

**Response (200):**
```json
{
  "success": true,
  "message": "User deactivated"
}
```

---

### POST /api/v1/users/{user_id}/reactivate

Reactivate user account.

**Response (200):**
```json
{
  "success": true,
  "message": "User reactivated"
}
```

---

### GET /api/v1/users/export/csv

Export users to CSV.

**Response (200):** CSV file download

---

## Role Management APIs

**Base:** `/api/v1/roles`  
**Auth Required:** Yes  
**Tenant Isolation:** Enforced

### GET /api/v1/roles

List available roles.

**Response (200):**
```json
[
  {
    "id": "uuid",
    "name": "TENANT_ADMIN",
    "description": "Full tenant administrator access",
    "composite": false
  }
]
```

---

### GET /api/v1/roles/{role_name}

Get role details including default entitlements.

**Response (200):**
```json
{
  "id": "uuid",
  "name": "SOC_ANALYST",
  "description": "SOC Analyst role",
  "composite": false,
  "default_entitlements": [
    "alert:*:read@{tenant_id}",
    "alert:*:triage@{tenant_id}"
  ]
}
```

---

### GET /api/v1/roles/users/{user_id}/roles

Get user's assigned roles.

**Response (200):**
```json
{
  "user_id": "uuid",
  "roles": [
    {"id": "uuid", "name": "TENANT_ADMIN", "description": "..."}
  ]
}
```

---

### POST /api/v1/roles/users/{user_id}/roles

Assign role to user (auto-grants entitlements).

**Request:**
```json
{
  "role_name": "SOC_ANALYST"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Role SOC_ANALYST assigned successfully",
  "entitlements_granted": [
    "alert:*:read@uuid",
    "alert:*:triage@uuid"
  ]
}
```

---

### DELETE /api/v1/roles/users/{user_id}/roles/{role_name}

Remove role from user.

**Response (200):**
```json
{
  "success": true,
  "message": "Role removed successfully"
}
```

---

### GET /api/v1/roles/{role_name}/permissions

Get default entitlements for a role.

**Response (200):**
```json
{
  "role": "SOC_MANAGER",
  "tenant_id": "uuid",
  "default_entitlements": ["..."],
  "count": 7,
  "description": "Default entitlements automatically granted..."
}
```

---

## MFA APIs

**Base:** `/api/v1/mfa`  
**Auth Required:** Yes  
**Tenant Isolation:** Enforced

### POST /api/v1/mfa/enroll

Initiate MFA enrollment for user.

**Request:**
```json
{
  "user_id": "uuid"
}
```

**Response (200):**
```json
{
  "secret": "base32-secret",
  "qr_code": "data:image/png;base64,...",
  "manual_entry_key": "base32-secret",
  "issuer": "SentinelGrid"
}
```

---

### POST /api/v1/mfa/verify-enrollment

Verify MFA enrollment with first code.

**Request:**
```json
{
  "user_id": "uuid",
  "code": "123456"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "MFA enrollment verified",
  "mfa_enabled": true
}
```

---

### GET /api/v1/mfa/{user_id}/status

Get MFA status for user.

**Response (200):**
```json
{
  "user_id": "uuid",
  "mfa_enabled": boolean,
  "mfa_type": "totp",
  "enrolled_at": "timestamp"
}
```

---

### DELETE /api/v1/mfa/{user_id}/disable

Disable MFA for user (admin only).

**Response (200):**
```json
{
  "success": true,
  "message": "MFA disabled successfully"
}
```

---

### GET /api/v1/mfa/{user_id}/recovery-codes

Get MFA recovery codes.

**Response (200):**
```json
{
  "codes": ["ABCD1234", "EFGH5678", ...],
  "generated_at": "timestamp"
}
```

---

## Audit Log APIs

**Base:** `/api/v1/audit-logs`  
**Auth Required:** Yes  
**Tenant Isolation:** Enforced

### GET /api/v1/audit-logs

List audit logs with filtering.

**Query Parameters:**
- `page` (int) - Page number
- `limit` (int, max: 1000) - Items per page
- `action` (string) - Filter by action
- `user_id` (string) - Filter by user
- `start_date` (datetime) - Start date
- `end_date` (datetime) - End date
- `resource_type` (string) - Filter by resource

**Response (200):**
```json
{
  "items": [
    {
      "id": "uuid",
      "timestamp": "datetime",
      "tenant_id": "uuid",
      "action": "user_login",
      "actor_user_id": "uuid",
      "actor_email": "string",
      "resource_type": "user",
      "resource_id": "uuid",
      "details": {},
      "ip_address": "string",
      "user_agent": "string",
      "result": "success"
    }
  ],
  "total": number,
  "page": number,
  "limit": number,
  "pages": number
}
```

---

### GET /api/v1/audit-logs/search

Search audit logs by text.

**Query Parameters:**
- `q` (string, required) - Search query
- `page` (int) - Page number
- `limit` (int) - Items per page

**Response (200):** Search results with items

---

### GET /api/v1/audit-logs/export

Export audit logs to CSV or JSON.

**Query Parameters:**
- `format` (string: "csv" or "json") - Export format
- `start_date` (datetime, optional) - Start date
- `end_date` (datetime, optional) - End date

**Response (200):** File download (CSV or JSON)

---

### GET /api/v1/audit-logs/stats

Get audit log statistics.

**Response (200):**
```json
{
  "tenant_id": "uuid",
  "total_events": number,
  "events_by_action": {"user_login": 150, ...},
  "events_by_user": {"user@example.com": 45, ...},
  "events_last_24h": number,
  "events_last_7d": number,
  "events_last_30d": number
}
```

---

## Security Notes

### Tenant Isolation

**ALL APIs enforce tenant isolation:**
- Users can ONLY access resources in their own tenant
- JWT token's `tenant_id` is the source of truth
- Cross-tenant access attempts return 403 Forbidden
- Error messages don't leak tenant information

### Authentication

**Required:** Bearer token in Authorization header
```
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Token contains:**
- `sub`: User ID
- `tenant_id`: Tenant ID (CRITICAL for isolation)
- `email`: User email
- `realm_access.roles`: User's roles

### Error Responses

**Standard Error Format:**
```json
{
  "detail": "Error message"
}
```

**Common Status Codes:**
- `200`: Success
- `201`: Created
- `400`: Bad request (validation error)
- `401`: Unauthorized (invalid/missing token)
- `403`: Forbidden (no permission or cross-tenant access)
- `404`: Not found (or cross-tenant resource)
- `409`: Conflict (duplicate resource)
- `500`: Internal server error

**Security:** 404 is returned for cross-tenant resources to prevent information leakage.

---

## Rate Limiting

**Limits:**
- Authentication: 10 requests/minute per IP
- API calls: 100 requests/minute per user
- Bulk operations: 10 requests/minute per user

**Headers:**
- `X-RateLimit-Limit`: Limit per window
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp

---

## Pagination

**Standard pagination parameters:**
- `page`: Page number (starts at 1)
- `limit`: Items per page (default: 50, max: 100)

**Response includes:**
- `items`: Array of results
- `total`: Total count
- `page`: Current page
- `limit`: Items per page
- `pages`: Total pages

---

## Examples

### Complete Signup → Login → API Call Flow

```bash
# 1. Signup
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Company",
    "email": "user@example.com",
    "password": "SecurePass123!",
    "first_name": "Test",
    "last_name": "User",
    "employee_count": 50
  }'

# Response: {"tenant_id": "abc-123", "user_id": "user-456", ...}

# 2. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'

# Response: {"access_token": "eyJ...", ...}

# 3. Use API with token
curl -X GET http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer eyJ..."

# Response: {"items": [...], "total": 10, ...}
```

---

## Changelog

**v1.0 (Dec 3, 2025):**
- Initial API reference
- User management APIs
- Role management APIs  
- MFA APIs
- Audit log APIs
- Multi-tenant isolation documented

---

## Support

For API support:
- Documentation: `/docs/archive/reference/identity/api-reference-iam.md`
- Interactive docs: `http://localhost:8000/docs` (Swagger UI)
- Security guide: `/docs/archive/reference/platform/multi-tenant-security.md`

