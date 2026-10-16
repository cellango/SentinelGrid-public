# seed_realms.py vs Password-Only Sync

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## What `seed_realms.py` Does

The `seed_realms.py` script does **much more** than just sync the password. It performs a full realm setup:

### 1. Creates/Updates Platform Admin Realm (`sg-admin`)
   - Creates the realm if it doesn't exist
   - Creates clients (web, API, IAM agent)
   - Creates roles (PLATFORM_ADMIN)
   - Creates/updates the platform admin user
   - **Syncs password from Vault** ✅ (this is part of it)

### 2. Creates Multi-Tenant Realms
   - Creates `sg-mt-us-1` realm
   - Creates `sg-mt-eu-1` realm
   - Creates clients, roles, client scopes for each
   - Configures protocol mappers

### 3. Seeds Database
   - Populates `realms` table in PostgreSQL
   - Links realm names to database records

### 4. Creates Test Users
   - Creates test customer user in `sg-mt-us-1`

### 5. Writes Credentials File
   - Creates `SEEDED_CREDENTIALS.txt` with all credentials

## If You Only Want to Sync the Password

If your realms already exist and you just need to update the password, use:

### Option 1: Simple Python Script
```bash
python backend/scripts/update_platform_admin_password.py
```

This script:
- ✅ Gets password from Vault
- ✅ Updates Keycloak user password only
- ❌ Doesn't create realms
- ❌ Doesn't create clients
- ❌ Doesn't seed database

### Option 2: Direct kcadm Command
```bash
# Get password from Vault
PASSWORD=$(docker exec -e VAULT_ADDR='http://127.0.0.1:8200' -e VAULT_TOKEN='sentinelgrid-dev-root-token' vault vault kv get -field=value sentinelgrid/keycloak/platform-admin-password)

# Update in Keycloak
docker exec keycloak /opt/keycloak/bin/kcadm.sh set-password \
    -r sg-admin \
    --username admin@sentinelgrid.ai \
    --new-password "$PASSWORD" \
    --server http://localhost:8080 \
    --realm master \
    --user admin \
    --password admin
```

## When to Use Each

| Scenario | Use This |
|----------|----------|
| First time setup | `seed_realms.py` |
| Realms already exist, just need password update | `update_platform_admin_password.py` |
| Quick one-time password sync | Direct `kcadm` command |
| After Vault restart, realms already setup | `update_platform_admin_password.py` |

## Summary

- **`seed_realms.py`** = Full realm setup + password sync
- **`update_platform_admin_password.py`** = Password sync only

For your case (Vault restarted, realms already exist), use the password-only script!

