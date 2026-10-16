# Sync Keycloak Password from Vault

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Problem

After Vault restarts and gets re-seeded with a new password, Keycloak still has the old password. This causes login failures.

## Solution

Use the existing `seed_realms.py` script which will:
1. Get the password from Vault
2. Update the Keycloak platform admin user password

## Quick Fix

```bash
python backend/scripts/seed_realms.py
```

This script already has logic to:
- Check if the platform admin user exists
- Update the password from Vault (line 246 in seed_realms.py)
- Create the user if it doesn't exist

## Manual Update (Alternative)

If you prefer to update just the password without running the full seed:

### Option 1: Using Python script
```bash
python backend/scripts/update_platform_admin_password.py
```

### Option 2: Using kcadm directly
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

## Platform Admin Details

- **Realm:** `sg-admin`
- **Username:** `admin@sentinelgrid.ai`
- **Password:** Retrieved from Vault at `sentinelgrid/keycloak/platform-admin-password`

## After Vault Restart

When Vault restarts in dev mode:
1. Run `backend/scripts/init_vault.sh` to re-seed Vault
2. Run `python backend/scripts/seed_realms.py` to sync password to Keycloak

