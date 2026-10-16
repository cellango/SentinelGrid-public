# IAM Portal Implementation

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Overview

The IAM Portal provides a frictionless, user-friendly interface for managing identity and access management without exposing Keycloak to customers. It implements three "hero" flows:

1. **Org Admin Adds User** - Simple user provisioning with access profiles
2. **Employee Requests Access** - Self-service access requests with approval workflow
3. **Admin Manages Roles & Entitlements** - Simple catalog of apps, roles, and access profiles

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ People Page  │  │ My Access    │  │ Apps &       │     │
│  │              │  │ Page         │  │ Profiles     │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                  │              │
│         └─────────────────┴──────────────────┘              │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              IAM Agent Service (FastAPI)                     │
│  ┌──────────────────────────────────────────────────────┐ │
│  │         IAM Portal API Endpoints                      │ │
│  │  /api/iam-portal/users                                 │ │
│  │  /api/iam-portal/apps                                 │ │
│  │  /api/iam-portal/entitlements                         │ │
│  │  /api/iam-portal/access-profiles                      │ │
│  │  /api/iam-portal/access-requests                     │ │
│  │  /api/iam-portal/my-access                           │ │
│  └──────────────────┬───────────────────────────────────┘ │
│                      │                                       │
│  ┌───────────────────▼───────────────────────────────────┐ │
│  │         IAM Portal Service                             │ │
│  │  - Business logic                                      │ │
│  │  - Keycloak integration                               │ │
│  │  - Audit logging                                       │ │
│  └──────────────────┬───────────────────────────────────┘ │
└──────────────────────┼─────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Keycloak (Per-Tenant Realm)                    │
│  - Users, Groups, Roles                                      │
│  - MFA Configuration                                        │
│  - SSO Sessions                                             │
└─────────────────────────────────────────────────────────────┘
```

### Data Model

The IAM Portal uses the following database schema:

- **apps** - Integrated applications (SentinelGrid, GitHub, AWS, Jira, etc.)
- **entitlements** - Logical permissions/roles
- **entitlement_mappings** - Maps entitlements to Keycloak groups/roles
- **access_profiles** - Bundles of entitlements (e.g., "Standard Employee", "Developer")
- **access_profile_entitlements** - Many-to-many relationship
- **user_entitlements** - Current entitlement assignments
- **access_requests** - Self-service access requests
- **approvals** - Approval workflow
- **iam_audit_log** - Audit trail for all IAM operations

## Implementation Details

### Database Migration

**Files:** 
- `backend/migrations/015_iam_portal_schema.sql` (IAM portal tables)
- `backend/migrations/002_realm_architecture.sql` (realms, customers, organizations, tenants)

Together these cover IAM portal data plus realm/org/tenant metadata needed for multi-realm placement.

### Backend Service Layer

**File:** `backend/services/iam_agent/app/services/iam_portal_service.py`

The `IAMPortalService` class provides:

- **User Management**: Create users, assign access profiles, grant/revoke entitlements
- **App & Entitlement Management**: Create apps, entitlements, and mappings to Keycloak
- **Access Profile Management**: Create and manage access profiles
- **Access Request Workflow**: Create requests, approve/deny with audit logging
- **Keycloak Integration**: Automatically syncs changes to Keycloak via Admin API

### API Endpoints

**Files:** 
- `backend/agents/iam_agent/app/api/iam_portal.py`
- `backend/agents/iam_agent/app/api/iam_orgs.py`

Key endpoints:

- `POST /api/iam-portal/users` - Create user (requires `tenant_id`, supports `team`, `department`)
- `GET /api/iam-portal/users` - List users (filters: `department`, `team`)
- `GET /api/iam-portal/users/{user_id}` - Get user details
- `POST /api/iam-portal/users/{user_id}/entitlements` - Grant entitlement
- `DELETE /api/iam-portal/users/{user_id}/entitlements/{entitlement_id}` - Revoke entitlement
- `POST /api/iam-portal/organizations` - Create organization with realm strategy (shared/dedicated/auto) and initial tenant
- `POST /api/iam-portal/organizations/{org_id}/tenants` - Create additional tenants under an org
- `GET /api/iam-portal/apps` - List apps
- `GET /api/iam-portal/entitlements` - List entitlements
- `GET /api/iam-portal/access-profiles` - List access profiles
- `POST /api/iam-portal/access-requests` - Create access request
- `GET /api/iam-portal/access-requests` - List access requests
- `POST /api/iam-portal/access-requests/{request_id}/approve` - Approve request
- `POST /api/iam-portal/access-requests/{request_id}/deny` - Deny request
- `GET /api/iam-portal/my-access` - Get current user's access summary

### Frontend Components

#### People Page
**File:** `frontend/src/app/(dashboard)/dashboard/iam/people/page.tsx`

- Data-grid UX: search, column visibility, sort, bulk select/export
- Filters by department and team
- Add user (requires tenant_id) with access profile assignment
- Shows status, department/team badges, and entitlement counts

#### My Access Page
**File:** `frontend/src/app/dashboard/iam/my-access/page.tsx`

- View current entitlements
- View pending requests
- Request new access with reason and optional duration
- See available entitlements

#### Apps & Access Profiles Page
**File:** `frontend/src/app/dashboard/iam/apps/page.tsx`

- View all apps and their available roles
- View access profiles and their entitlements
- See risk levels and privileged flags

#### IAM Layout
**File:** `frontend/src/app/dashboard/iam/layout.tsx`

Provides sub-navigation for IAM portal pages.

### API Client

**File:** `frontend/src/lib/api/iam-portal.ts`

TypeScript client for IAM portal API with type definitions.

## Key Features

### 1. Frictionless User Provisioning

**Flow:**
1. Admin goes to People → Add User
2. Fills form: Name, Email, Department, Access Profile
3. Clicks "Invite User"
4. User receives email to set password and enroll MFA
5. User automatically gets entitlements from selected profile

**Behind the scenes:**
- IAM Service creates user in Keycloak
- Assigns Keycloak groups/roles based on access profile
- Logs audit event
- Sends invitation email (via Keycloak)

### 2. Self-Service Access Requests

**Flow:**
1. Employee goes to My Access
2. Views available entitlements
3. Clicks "Request Access" on desired entitlement
4. Fills reason and optional duration
5. Request goes to approvers (manager, app owner, admin)
6. Approver approves/denies with one click
7. If approved, entitlement is automatically granted

**Behind the scenes:**
- IAM Service creates access request
- Determines approvers based on entitlement risk level
- Creates approval records
- On approval, grants entitlement via Keycloak
- Logs audit event
- Optionally triggers SOAR playbook for external provisioning

### 3. Simple Role & Entitlement Management

**Flow:**
1. Admin goes to Apps & Access Profiles
2. Views apps and their available roles
3. Views access profiles and their entitlements
4. Creates new access profile by selecting entitlements
5. Assigns profile to users

**Behind the scenes:**
- IAM Service stores profile in database
- Maps entitlements to Keycloak groups/roles
- When profile assigned, all entitlements granted automatically

## Keycloak Integration

The IAM Portal abstracts Keycloak completely. Customers never see:

- Keycloak groups
- Keycloak roles
- Keycloak clients
- Keycloak realms

Instead, they see:

- **Users** - Simple user objects
- **Apps** - Applications (SentinelGrid, GitHub, AWS, etc.)
- **Entitlements** - Logical permissions (e.g., "GitHub: Admin", "AWS: Read-only")
- **Access Profiles** - Bundles of entitlements (e.g., "Developer", "Finance")

The `IAMPortalService` maintains a mapping table (`entitlement_mappings`) that translates entitlements to Keycloak artifacts:

```python
entitlement_id → {
    realm_name: "tenant-realm",
    keycloak_group_name: "github-admins",
    keycloak_role_name: "GITHUB_ADMIN",
    keycloak_client_id: "github-client"
}
```

When an entitlement is granted:
1. IAM Service looks up mappings
2. Calls Keycloak Admin API to add user to groups/roles
3. Optionally provisions in external systems (GitHub, Jira, etc.)

## Security & Audit

### Audit Logging

All IAM operations are logged to `iam_audit_log`:

- User created
- Entitlement granted
- Entitlement revoked
- Access requested
- Access approved/denied

Each log entry includes:
- Actor (who performed the action)
- Target (user, entitlement, request)
- Timestamp
- IP address
- User agent
- Additional details (JSON)

### Security Features

- **Token-based authentication** - All API calls require valid JWT token
- **Tenant isolation** - All operations are scoped to tenant
- **Privileged role approval** - High-risk entitlements require approval
- **MFA enforcement** - Can require MFA for privileged roles
- **Temporary access** - Support for time-limited access

## Usage Examples

### Creating a User

```typescript
const userData = {
  username: "john.doe@example.com",
  email: "john.doe@example.com",
  first_name: "John",
  last_name: "Doe",
  department: "Engineering",
  access_profile_id: "developer-profile-uuid",
  make_admin: false
};

await createIAMUser(userData);
```

### Requesting Access

```typescript
const requestData = {
  entitlement_id: "github-admin-uuid",
  reason: "Need to manage repository settings for new project",
  duration_days: 30  // Optional: temporary access
};

await createAccessRequest(requestData);
```

### Approving Access Request

```typescript
await approveAccessRequest(requestId, "Approved for project work");
```

## Future Enhancements

1. **HR/Directory Connector** - Sync from Google Workspace, Entra, etc.
2. **Automated Access Reviews** - Periodic review of user access
3. **Risk Scoring** - AI-powered risk assessment for access requests
4. **External Provisioning** - Automatic provisioning in GitHub, Jira, AWS, etc.
5. **Access Packages** - Time-bound bundles of access
6. **Delegated Administration** - Allow department admins to manage their teams

## Testing

### Backend Testing

```bash
cd backend/services/iam_agent
pytest tests/test_iam_portal_service.py
```

### Frontend Testing

```bash
cd frontend
npm test -- iam
```

## Configuration

### Environment Variables

```bash
# IAM Agent
IAM_AGENT_URL=http://iam_agent:8000
KEYCLOAK_URL=http://keycloak:8080
KEYCLOAK_REALM=sentinelgrid
KEYCLOAK_CLIENT_ID=sentinelgrid-iam-agent
KEYCLOAK_CLIENT_SECRET=<secret>

# Frontend
NEXT_PUBLIC_IAM_AGENT_URL=http://localhost:8000
```

## Migration

To apply the database migration:

```bash
psql -U sg -d sg -f backend/migrations/015_iam_portal_schema.sql
```

Or via migration tool:

```bash
python backend/scripts/run_migrations.py
```

## Troubleshooting

### Users not appearing in People page

1. Check tenant_id in JWT token
2. Verify Keycloak user has `tenant_id` attribute
3. Check IAM Agent logs for errors

### Access requests not working

1. Verify entitlement mappings exist
2. Check Keycloak Admin API connectivity
3. Review audit logs for errors

### Keycloak sync issues

1. Verify service account has admin permissions
2. Check realm name matches tenant
3. Review IAM Agent logs

## Support

For issues or questions, contact the SentinelGrid team or check the main documentation.
