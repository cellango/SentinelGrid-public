# Resolving Keycloak Master Admin Password Mismatch

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Problem

After Vault is re-seeded/reinitialized, it generates a new master admin password. However, Keycloak still has the old password stored, causing authentication failures.

**Symptoms:**
- Cannot sign in as admin using password from Vault
- Authentication fails with "Invalid user credentials"
- Password sync scripts fail because they can't authenticate

## Root Cause

Vault was re-seeded (data lost in dev mode or reinitialized), generating a new password. Keycloak database still has the old password hash.

## Quick Solutions

### Solution 1: Update Vault to Match Current Keycloak Password ⭐ RECOMMENDED

If you know what Keycloak's current password is:

```bash
# Use the helper script
backend/scripts/update_vault_from_keycloak.sh "current-password"

# Or manually
docker exec -e VAULT_ADDR='http://127.0.0.1:8200' \
  -e VAULT_TOKEN='sentinelgrid-dev-root-token' \
  vault vault kv put sentinelgrid/keycloak/master-admin-password value="current-password"
```

**This is the simplest solution** - just update Vault to match Keycloak!

### Solution 2: Reinitialize Keycloak (For Dev Environments)

If you're okay losing Keycloak data (realms, users, etc.):

```bash
# 1. Stop Keycloak
docker-compose -f docker-compose.dev.yml stop keycloak

# 2. Remove Keycloak data volume (⚠️ DELETES ALL DATA)
docker volume rm sentinelgrid_keycloak_data

# 3. Re-seed Vault (if not already done)
backend/scripts/init_vault.sh

# 4. Start Keycloak (will use default password 'admin')
docker-compose -f docker-compose.dev.yml up -d keycloak

# 5. Wait for Keycloak to start (60 seconds)
sleep 60

# 6. Sync master admin password from Vault
backend/scripts/sync_master_admin_password_simple.sh

# 7. Run realm seeding
python backend/scripts/seed_realms.py
```

⚠️ **Warning:** This deletes all Keycloak data including realms, users, and clients!

## Detailed Solutions

### Check Current Keycloak Password

First, let's see if Keycloak still uses the default password:

```bash
# Test default password
docker exec sentinelgrid-keycloak-1 /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin 2>&1 | head -2
```

If this works, Keycloak is using "admin" - update Vault:
```bash
backend/scripts/update_vault_from_keycloak.sh "admin"
```

### Update Vault Script

Created helper script:
```bash
backend/scripts/update_vault_from_keycloak.sh "password-here"
```

This updates Vault to match Keycloak's current password.

## Recommended Approach

**For Development:**
1. Try default password "admin" first
2. If that works, update Vault: `backend/scripts/update_vault_from_keycloak.sh "admin"`
3. If not, and you know the password, update Vault to match it
4. If you don't know the password, consider reinitializing (Solution 2)

**For Production:**
1. Check backups for current password
2. Update Vault to match current password (Solution 1)
3. Document the change
4. Never use Solution 2 in production!

## Prevention

To prevent this in the future:

1. **Use persistent Vault storage** (not dev mode) for production
2. **Backup Vault regularly**
3. **Document password changes**
4. **Run sync scripts immediately after Vault re-seeding**

## Scripts Available

- `backend/scripts/update_vault_from_keycloak.sh` - Update Vault to match Keycloak ⭐ NEW
- `backend/scripts/update_master_admin_password.py` - Sync from Vault (requires auth)
- `backend/scripts/sync_master_admin_password_simple.sh` - Sync using kcadm.sh

## Quick Reference

```bash
# Get password from Vault
docker exec -e VAULT_ADDR='http://127.0.0.1:8200' \
  -e VAULT_TOKEN='sentinelgrid-dev-root-token' \
  vault vault kv get -field=value sentinelgrid/keycloak/master-admin-password

# Update Vault to match Keycloak (if you know Keycloak's password)
backend/scripts/update_vault_from_keycloak.sh "known-password"

# Test if default password works
docker exec sentinelgrid-keycloak-1 /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin
```
