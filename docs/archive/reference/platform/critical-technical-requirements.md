# Critical Technical Requirements - Realm Creation & User Profile Configuration

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Status:** ACTIVE  
**Last Updated:** 2025-01-28  
**Priority:** CRITICAL - Foundational Requirement

---

## Overview

This document defines **critical technical requirements** for Keycloak realm creation and User Profile configuration in SentinelGrid. These requirements are **non-negotiable** and must be followed for the system to function correctly.

**Violation of these requirements will result in:**
- Users not having `tenant_id` in their attributes
- JWT tokens not including `tenant_id` claim
- Multi-tenant isolation failures
- System non-functionality

---

## Requirement 1: All Realm Creation MUST Go Through Centralized API

### Rule

**ALL Keycloak realms MUST be created via the centralized realm creation API:**

```
POST /api/v1/realms
```

**NO EXCEPTIONS.**

### Rationale

The centralized API ensures:
- User Profile is automatically configured with `tenant_id` attribute
- Naming conventions are enforced
- Standard clients, roles, and protocol mappers are created
- Consistency across all realms

### Implementation

- **API Endpoint:** `backend/agents/iam_agent/app/api/realms.py`
- **Service Layer:** `backend/agents/iam_agent/app/services/realm_creation_service.py`
- **Library:** `backend/libs/sg_core/keycloak_user_profile.py`

### Migration Status

All existing realm creation code has been migrated:
- ✅ `backend/scripts/seed_realms.py`
- ✅ `backend/scripts/seed_demo_data.py`
- ✅ `backend/agents/iam_agent/app/services/realm_manager.py`
- ✅ `backend/agents/iam_agent/app/services/multi_tenant_realm_manager.py`

### Consequences of Non-Compliance

If realms are created outside the centralized API:
- User Profile may not be configured
- Custom attributes (`tenant_id`) will NOT persist
- JWT tokens will NOT include `tenant_id` claim
- Multi-tenant isolation will FAIL

---

## Requirement 2: User Profile MUST Be Configured with tenant_id Attribute

### Rule

**User Profile MUST be configured with `tenant_id` attribute BEFORE creating any users in a realm.**

This is a **Keycloak v25+ requirement** - NOT optional.

### Rationale

Keycloak v25+ (we're on v26.4.7) requires custom attributes to be defined in the **User Profile schema** before they can persist. Without this configuration:
- User attribute setting attempts will fail silently
- `tenant_id` will not be stored in user objects
- Protocol mappers cannot read `tenant_id`
- JWT tokens will not include `tenant_id` claim

### Implementation

The User Profile configuration is automatically handled by:
1. **RealmCreationService** - Configures User Profile during realm creation
2. **Fail-safe mechanisms** - Onboarding services verify and configure User Profile before creating users

### User Profile Schema

The User Profile must include:

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

### Verification

To verify User Profile is configured:

```bash
# Via API
GET /api/v1/realms/{realm_name}/status

# Response includes:
{
  "realm_name": "demo",
  "exists": true,
  "user_profile_configured": true,
  "keycloak_realm_id": "..."
}
```

### Consequences of Non-Compliance

If User Profile is not configured:
- Users created during onboarding won't have `tenant_id` in attributes
- Protocol mapper can't read `tenant_id` because it doesn't exist
- JWT tokens won't include `tenant_id` claim
- Multi-tenant isolation fails
- System is non-functional

---

## Requirement 3: Naming Conventions MUST Be Enforced

### Rule

**All realm names MUST follow strict naming conventions:**

| Realm Type | Naming Convention | Example |
|------------|-------------------|---------|
| Platform Admin | `sg-admin` | `sg-admin` |
| Multi-Tenant | `sg-mt-{region}-{shard}` | `sg-mt-us-1`, `sg-mt-eu-1` |
| Dedicated Customer | `{customer-slug}` | `agribotsai`, `acme-corp` |
| Demo | `demo` | `demo` |

### Validation Rules

- **Platform Admin:** Must be exactly `sg-admin`
- **Multi-Tenant:** Must match pattern `sg-mt-{region}-{shard}` where:
  - `region` is lowercase (e.g., `us`, `eu`, `ap`)
  - `shard` is a number (e.g., `1`, `2`, `3`)
- **Dedicated Customer:** Must be a valid slug:
  - Lowercase alphanumeric with hyphens/underscores
  - Max 50 characters
  - Must match `customer_slug` parameter
- **Demo:** Must be exactly `demo`

### Implementation

Naming conventions are enforced by:
- **RealmCreationService._validate_realm_name()** - Validates before realm creation
- **API endpoint** - Returns 400 Bad Request for invalid names

### Consequences of Non-Compliance

If naming conventions are violated:
- Realm creation will fail with clear error message
- System cannot track or manage realms correctly
- Potential conflicts with existing realms

---

## Requirement 4: Protocol Mappers MUST Be Configured

### Rule

**All realms MUST have protocol mappers configured to include `tenant_id` in JWT tokens.**

### Implementation

Protocol mappers are automatically created by `RealmCreationService`:
- Mapper name: `tenant-id-mapper`
- Mapper type: `oidc-usermodel-attribute-mapper`
- User attribute: `tenant_id`
- Token claim: `tenant_id`
- Added to: ID token, access token, userinfo token

### Consequences of Non-Compliance

If protocol mappers are not configured:
- JWT tokens will not include `tenant_id` claim
- API Gateway cannot extract `tenant_id` from tokens
- Multi-tenant isolation fails
- System is non-functional

---

## Requirement 5: Fail-Safe Mechanisms MUST Be Present

### Rule

**All user creation services MUST verify User Profile is configured before creating users.**

If User Profile is not configured, services MUST attempt to configure it automatically (fail-safe).

### Implementation

Fail-safe mechanisms are implemented in:
- ✅ `IAMPortalService.create_user()`
- ✅ `InvitationService.create_invitation()`
- ✅ `BulkImportService.import_users()`

### Behavior

1. **Check:** Verify User Profile has `tenant_id` attribute
2. **Configure:** If missing, attempt to configure automatically
3. **Log:** Log warning/error if configuration fails
4. **Continue:** Allow user creation to continue (graceful degradation)

### Consequences of Non-Compliance

Without fail-safe mechanisms:
- Users may be created without `tenant_id` if realm was misconfigured
- System may fail silently
- Difficult to diagnose issues

---

## Compliance Checklist

When creating a new realm, verify:

- [ ] Realm is created via `POST /api/v1/realms` API
- [ ] User Profile is configured with `tenant_id` attribute
- [ ] Naming convention is followed
- [ ] Protocol mappers are configured
- [ ] Standard clients are created (web, api, iam-agent)
- [ ] Standard roles are created (TENANT_ADMIN, SOC_MANAGER, SOC_ANALYST, VIEW_ONLY)

When creating a new user, verify:

- [ ] User creation service has fail-safe User Profile verification
- [ ] `tenant_id` attribute is set on user
- [ ] JWT token includes `tenant_id` claim

---

## Enforcement

### Code Review

All code changes that:
- Create realms
- Create users
- Modify User Profile configuration

MUST be reviewed to ensure compliance with these requirements.

### Testing

All realm creation and user creation code MUST be tested to verify:
- User Profile is configured
- `tenant_id` attributes persist
- JWT tokens include `tenant_id` claim

### Monitoring

Production systems MUST monitor:
- Realm creation events (verify User Profile configuration)
- User creation events (verify `tenant_id` attribute is set)
- JWT token validation (verify `tenant_id` claim is present)

---

## Related Documentation

- [Realm Creation API Documentation](../identity/realm-creation-api.md)
- [Keycloak User Profile Configuration](../../../../scripts/configure_user_profile.sh)
- [Multi-Tenant Architecture](../../README.md#retired-references)

---

## Questions or Issues

If you have questions or encounter issues related to these requirements:

1. Check this document first
2. Review the implementation in `RealmCreationService`
3. Check API documentation in `REALM_CREATION_API.md`
4. Contact the platform team

**Remember: These requirements are CRITICAL and NON-NEGOTIABLE.**

