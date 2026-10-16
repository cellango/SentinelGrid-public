# Keycloak Configuration

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This directory contains Keycloak realm configuration files.

## Files

- `realm-export.json` - SentinelGrid realm configuration (to be generated/created)

## Setup Instructions

### 1. Initial Setup (Development)

For development, Keycloak starts in dev mode with auto-import enabled.

The realm will be automatically imported from `realm-export.json` on first startup.

### 2. Manual Realm Configuration

If you need to configure manually:

1. Start Keycloak: `docker-compose up keycloak`
2. Access admin console: http://localhost:8081
3. Login: admin / admin (or your configured password)
4. Create realm: "sentinelgrid"
5. Configure clients, roles, protocol mappers

### 3. Export Realm Configuration

Once configured, export the realm:

```bash
# From Keycloak admin console:
# Realm Settings → Export → Export realm

# Or via CLI:
docker-compose exec keycloak /opt/keycloak/bin/kcadm.sh \
  get realms/sentinelgrid -r master > realm-export.json
```

### 4. Realm Configuration Checklist

- [ ] Create realm: `sentinelgrid`
- [ ] Create client: `sentinelgrid-web` (public, OIDC)
- [ ] Create client: `sentinelgrid-api` (confidential, OIDC)
- [ ] Create client: `sentinelgrid-iam-agent` (service account, Admin API access)
- [ ] Create roles: TENANT_ADMIN, SOC_MANAGER, SOC_ANALYST, VIEW_ONLY
- [ ] Configure protocol mapper: `tenant_id` mapper
- [ ] Set up user attribute: `tenant_id` on users

## Protocol Mapper for tenant_id

Add a protocol mapper to include `tenant_id` in tokens:

1. Clients → sentinelgrid-api → Mappers → Create
2. Name: `tenant-id-mapper`
3. Mapper Type: `User Attribute`
4. User Attribute: `tenant_id`
5. Token Claim Name: `tenant_id`
6. Claim JSON Type: `String`
7. Add to ID token: `ON`
8. Add to access token: `ON`

## Service Account Setup

For `sentinelgrid-iam-agent` client:

1. Enable "Service accounts roles"
2. Assign realm roles: `admin` (or create custom service account role)
3. Save client secret for IAM Agent configuration

