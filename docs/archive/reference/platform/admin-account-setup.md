# Keycloak Admin Account Setup

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Current Status

- ✅ Default `admin` account is **disabled** (security best practice)
- ⏳ Need to create dedicated `sentinelgrid-admin` account
- ✅ IAM Agent configured to use `sentinelgrid-admin` account
- ✅ Docker-compose updated with new credentials

## ⚠️ IMMEDIATE ACTION REQUIRED

The `sentinelgrid-admin` account **must be created** before signup will work.

## Setup Instructions

### Option 1: Via Keycloak Admin Console (Recommended - Easiest)

1. Access Keycloak Admin Console: http://localhost:8081/admin
2. Login with default credentials (if enabled) or use environment variables:
   - Username: `admin`
   - Password: Check `KEYCLOAK_ADMIN_PASSWORD` environment variable (default: `admin`)

3. Navigate to: **Users** → **Add user**
4. Create user:
   - Username: `sentinelgrid-admin`
   - Email: `sentinelgrid-admin@sentinelgrid.local`
   - First name: `SentinelGrid`
   - Last name: `Admin`
   - Enabled: `ON`

5. Set password:
   - Go to **Credentials** tab
   - Set password: `SentinelGridAdmin2024!`
   - Temporary: `OFF`

6. Assign admin role:
   - Go to **Role Mappings** tab
   - Click **Assign role**
   - Filter by: **Filter by realm roles**
   - Select: `admin`
   - Click **Assign**

### Option 2: Enable Default Admin Temporarily, Then Create Account

If you cannot access the web UI, you can temporarily enable the default admin:

```bash
# Enable admin account temporarily
./scripts/enable-admin-temporarily.sh

# Then create sentinelgrid-admin account
./scripts/create-sentinelgrid-admin.sh

# ⚠️ IMPORTANT: Disable default admin again after setup!
```

### Option 3: Via Script (If Admin Account Enabled)

```bash
./scripts/create-sentinelgrid-admin.sh
```

If you need to enable the default admin account temporarily:

```bash
# Access Keycloak container
docker-compose exec keycloak bash

# Use kcadm to enable admin
/opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 \
  --realm master \
  --user admin \
  --password admin

# Enable admin user
/opt/keycloak/bin/kcadm.sh update users -r master \
  -s username=admin -s enabled=true
```

**⚠️ Remember to disable the default admin account after creating the new account!**

## Verification

After creating the account, verify it works:

```bash
# IAM Agent should already be running with new credentials
# Check logs to see if it connected
docker-compose logs iam_agent | grep -i "connected\|error" | tail -5
```

You should see:
```
Connected to Keycloak admin at http://keycloak:8080
```

If you see errors, check:
1. Account exists: `docker-compose exec keycloak /opt/keycloak/bin/kcadm.sh get users -r master -q username=sentinelgrid-admin`
2. Account is enabled
3. Account has admin role assigned
4. Password matches what's in docker-compose.dev.yml

## Production Migration

**Before production**, migrate to service account authentication:
- See `docs/archive/reference/identity/keycloak-service-account-migration.md`
- Tracked in `docs/PRODUCTION_READINESS_TODO.md`

