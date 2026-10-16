# SentinelGrid IAM Developer Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Version:** 1.0  
**Date:** 2025-01-28  
**Audience:** Developers

---

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)
6. [Examples](#examples)

---

## API Overview

The SentinelGrid IAM API provides programmatic access to identity and access management features.

### Base URL

```
Production: https://api.sentinelgrid.com
Development: http://localhost:8000
```

### API Versioning

All endpoints are versioned: `/api/v1/...`

### Response Format

All responses are JSON:

```json
{
  "success": true,
  "data": {...},
  "message": "Operation successful"
}
```

### Error Format

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-01-28T12:00:00Z"
}
```

---

## Authentication

### Getting an Access Token

#### OAuth 2.0 / OIDC Flow

```bash
# 1. Get authorization code (frontend redirect)
GET /realms/sentinelgrid/protocol/openid-connect/auth?
  client_id=sentinelgrid-web&
  redirect_uri=https://app.example.com/callback&
  response_type=code&
  scope=openid email profile

# 2. Exchange code for token
POST /realms/sentinelgrid/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code=AUTHORIZATION_CODE&
redirect_uri=https://app.example.com/callback&
client_id=sentinelgrid-web
```

#### Direct Access Grant (Service Accounts)

```bash
POST /realms/sentinelgrid/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

grant_type=password&
client_id=sentinelgrid-api&
client_secret=CLIENT_SECRET&
username=service-account&
password=PASSWORD
```

### Using the Token

Include the token in the `Authorization` header:

```bash
Authorization: Bearer <access_token>
```

### Token Claims

JWT tokens include:
- `sub`: User ID
- `email`: User email
- `tenant_id`: Tenant identifier (for multi-tenancy)
- `roles`: User roles
- `exp`: Expiration timestamp

---

## API Endpoints (IAM Portal)

**Base path:** `/api/iam-portal`

### User Management

#### List Users

```bash
GET /api/iam-portal/users?department=Engineering&team=Platform
Authorization: Bearer <token>
```

**Response (array):**
```json
[
  {
    "user_id": "user-123",
    "username": "john.doe@example.com",
    "email": "john.doe@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "enabled": true,
    "tenant_id": "tenant-456",
    "department": "Engineering",
    "team": "Platform",
    "entitlements": []
  }
]
```

#### Create User

```bash
POST /api/iam-portal/users
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "newuser@example.com",
  "email": "newuser@example.com",
  "tenant_id": "tenant-456",          // required
  "first_name": "New",
  "last_name": "User",
  "department": "Engineering",
  "team": "Platform",
  "access_profile_id": "profile-uuid", // optional
  "make_admin": false
}
```

#### Bulk Upload Users

See User Onboarding API if applicable; otherwise use the self-service onboarding endpoints.

### Organizations & Tenants (Realm Strategy)

- `POST /api/iam-portal/organizations`
  - Body: `name`, optional `display_name`, `realm_strategy` (`shared|dedicated|auto`), `region` (default `us`), `projected_user_count`
  - Picks or creates realm (auto resolves to shared/dedicated based on projected users), provisions initial tenant
- `POST /api/iam-portal/organizations/{org_id}/tenants`
  - Body: `tenant_name`, optional `tenant_slug`, `region` (default `us`)
  - Adds a tenant under the org, reusing the org realm

Responses include `realm_name` and `keycloak_org_id`/`keycloak_group_id`; use returned `tenant_id` when creating users.

### Self-Service

#### Get Profile

```bash
GET /api/v1/self/profile
Authorization: Bearer <token>
```

#### Update Profile

```bash
PUT /api/v1/self/profile
Authorization: Bearer <token>
Content-Type: application/json

{
  "firstName": "Updated",
  "lastName": "Name",
  "locale": "en",
  "timezone": "America/New_York"
}
```

#### Change Password

```bash
POST /api/v1/self/password/change
Authorization: Bearer <token>
Content-Type: application/json

{
  "current_password": "oldpass123",
  "new_password": "newpass123"
}
```

#### List Active Sessions

```bash
GET /api/v1/self/sessions
Authorization: Bearer <token>
```

### Authentication

#### Passwordless - Send Magic Link

```bash
POST /api/v1/auth/passwordless/magic-link
Content-Type: application/json

{
  "email": "user@example.com",
  "redirect_uri": "https://app.example.com/callback"
}
```

#### Passwordless - Send OTP

```bash
POST /api/v1/auth/passwordless/otp
Content-Type: application/json

{
  "email": "user@example.com"
}
```

#### Passwordless - Verify

```bash
POST /api/v1/auth/passwordless/verify
Content-Type: application/json

{
  "token": "magic-link-token",
  "code": "123456"  // Optional for OTP
}
```

### App Catalog

#### List Apps

```bash
GET /api/v1/apps/catalog?category=Productivity&search=Microsoft
Authorization: Bearer <token>
```

#### Connect App

```bash
POST /api/v1/apps/catalog/microsoft_365/connect
Authorization: Bearer <token>
Content-Type: application/json

{
  "catalog_app_id": "microsoft_365",
  "config": {
    "redirect_uri": "https://login.microsoftonline.com/saml",
    "entity_id": "https://sts.windows.net/tenant-id/"
  }
}
```

### Security

#### List Anomalies

```bash
GET /api/v1/security/anomalies?severity=high&status=open
Authorization: Bearer <token>
```

#### Acknowledge Anomaly

```bash
POST /api/v1/security/anomalies/{anomaly_id}/acknowledge
Authorization: Bearer <token>
Content-Type: application/json

{
  "notes": "Reviewed and resolved"
}
```

### Reports

#### Generate Login History Report

```bash
GET /api/v1/reports/login-history?start_date=2025-01-01&end_date=2025-01-31&format=csv
Authorization: Bearer <token>
```

Returns CSV file download.

#### Generate MFA Adoption Report

```bash
GET /api/v1/reports/mfa-adoption?format=csv
Authorization: Bearer <token>
```

### Privileged Access

#### Request Privileged Access

```bash
POST /api/v1/privileged-access/request
Authorization: Bearer <token>
Content-Type: application/json

{
  "resource_type": "role",
  "resource_id": "ADMIN_ROLE",
  "resource_name": "Administrator Role",
  "reason": "Need to perform system maintenance",
  "duration_hours": 2
}
```

#### Approve Request

```bash
POST /api/v1/privileged-access/requests/{request_id}/approve
Authorization: Bearer <token>
Content-Type: application/json

{
  "comments": "Approved for maintenance"
}
```

### Secrets

#### Create Secret

```bash
POST /api/v1/secrets
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Database Password",
  "description": "Production database password",
  "secret_type": "password",
  "value": "secure-password-123",
  "rotation_days": 90
}
```

**Response includes full secret (shown only once):**
```json
{
  "id": "secret-123",
  "name": "Database Password",
  "secret_type": "password",
  "key": "sg_tenant_abc123..."  // Full secret - save immediately!
}
```

#### Rotate Secret

```bash
POST /api/v1/secrets/{secret_id}/rotate
Authorization: Bearer <token>
```

### API Keys

#### Create API Key

```bash
POST /api/v1/api-keys
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Production API Key",
  "scopes": ["read:users", "write:users"],
  "rate_limit_per_minute": 60,
  "rate_limit_per_hour": 1000,
  "expires_in_days": 365
}
```

**Response includes full key (shown only once):**
```json
{
  "id": "key-123",
  "name": "Production API Key",
  "key": "sg_tenant_xyz789..."  // Full key - save immediately!
}
```

#### Using API Keys

```bash
Authorization: Bearer <api_key>
```

---

## Error Handling

### HTTP Status Codes

- `200 OK`: Success
- `201 Created`: Resource created
- `400 Bad Request`: Invalid request
- `401 Unauthorized`: Missing or invalid token
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

### Error Response Example

```json
{
  "detail": "User not found",
  "error_code": "USER_NOT_FOUND",
  "timestamp": "2025-01-28T12:00:00Z"
}
```

### Common Error Codes

- `INVALID_TOKEN`: Token is invalid or expired
- `MISSING_TENANT_ID`: Token missing tenant_id claim
- `INSUFFICIENT_PERMISSIONS`: User lacks required role
- `TENANT_ISOLATION_VIOLATION`: Attempted cross-tenant access
- `VALIDATION_ERROR`: Request validation failed
- `RESOURCE_NOT_FOUND`: Requested resource doesn't exist

---

## Rate Limiting

API requests are rate-limited:

- **Per user**: 100 requests per minute
- **Per tenant**: 1000 requests per hour
- **API keys**: Configurable per key

### Rate Limit Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704067200
```

### Rate Limit Exceeded

```json
{
  "detail": "Rate limit exceeded",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60
}
```

---

## Examples

### Python Example

```python
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "your-access-token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# List users
response = requests.get(
    f"{BASE_URL}/api/v1/users",
    headers=headers,
    params={"page": 1, "limit": 50}
)
users = response.json()

# Invite user
response = requests.post(
    f"{BASE_URL}/api/v1/users/invite",
    headers=headers,
    json={
        "email": "newuser@example.com",
        "firstName": "New",
        "lastName": "User",
        "send_email": True
    }
)
invitation = response.json()

# Get profile
response = requests.get(
    f"{BASE_URL}/api/v1/self/profile",
    headers=headers
)
profile = response.json()
```

### JavaScript/TypeScript Example

```typescript
const BASE_URL = 'http://localhost:8000';
const TOKEN = 'your-access-token';

const headers = {
  'Authorization': `Bearer ${TOKEN}`,
  'Content-Type': 'application/json'
};

// List users
const usersResponse = await fetch(
  `${BASE_URL}/api/v1/users?page=1&limit=50`,
  { headers }
);
const users = await usersResponse.json();

// Invite user
const inviteResponse = await fetch(
  `${BASE_URL}/api/v1/users/invite`,
  {
    method: 'POST',
    headers,
    body: JSON.stringify({
      email: 'newuser@example.com',
      firstName: 'New',
      lastName: 'User',
      send_email: true
    })
  }
);
const invitation = await inviteResponse.json();
```

### cURL Examples

```bash
# List users
curl -X GET "http://localhost:8000/api/v1/users" \
  -H "Authorization: Bearer $TOKEN"

# Invite user
curl -X POST "http://localhost:8000/api/v1/users/invite" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "firstName": "New",
    "lastName": "User"
  }'

# Get profile
curl -X GET "http://localhost:8000/api/v1/self/profile" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Multi-Tenancy

All API endpoints enforce tenant isolation:

- **Tenant ID** is extracted from JWT token
- Users can only access resources in their tenant
- Cross-tenant access is blocked
- All responses are filtered by tenant_id

### Tenant Isolation Example

```python
# User in tenant-123 can only see users in tenant-123
response = requests.get(
    f"{BASE_URL}/api/v1/users",
    headers={"Authorization": f"Bearer {token_tenant_123}"}
)
# Returns only users with tenant_id="tenant-123"
```

---

## Webhooks (Future)

Webhook support for real-time notifications:

- User created/updated/deleted
- Access granted/revoked
- Security anomaly detected
- Policy violation

---

## SDKs (Future)

Official SDKs planned:

- Python SDK
- JavaScript/TypeScript SDK
- Go SDK

---

## Support

- **API Documentation**: See OpenAPI/Swagger docs at `/docs`
- **Issues**: Report via GitHub or support portal
- **Questions**: Contact developer support

---

**Last Updated:** 2025-01-28
