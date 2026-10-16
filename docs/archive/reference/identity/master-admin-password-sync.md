# Master Admin Password Sync

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Summary

Created scripts to sync the master admin password from Vault to Keycloak, following the same pattern as the platform admin password sync.

## Scripts Created

### 1. Python Script
**File:** `backend/scripts/update_master_admin_password.py`

**Features:**
- Gets master admin password from Vault (`sentinelgrid/keycloak/master-admin-password`)
- No environment variables for passwords (secure)
- Tries default password first, then Vault password
- Updates master realm admin user password

**Usage:**
```bash
python backend/scripts/update_master_admin_password.py
```

### 2. Bash Script
**File:** `backend/scripts/sync_master_admin_password_simple.sh`

**Features:**
- Uses `kcadm.sh` directly (most reliable)
- Gets password from Vault only (no env vars)
- Simple and straightforward

**Usage:**
```bash
backend/scripts/sync_master_admin_password_simple.sh
```

## Pattern Comparison

### Platform Admin Sync
1. Gets password from Vault: `sentinelgrid/keycloak/platform-admin-password`
2. Authenticates to Keycloak using master admin
3. Updates user: `admin@sentinelgrid.ai` in `sg-admin` realm

### Master Admin Sync (Same Pattern)
1. Gets password from Vault: `sentinelgrid/keycloak/master-admin-password`
2. Authenticates to Keycloak using current master admin (default or Vault)
3. Updates user: `admin` in `master` realm

## Key Differences

| Aspect | Platform Admin | Master Admin |
|--------|----------------|--------------|
| Realm | `sg-admin` | `master` |
| Username | `admin@sentinelgrid.ai` | `admin` |
| Vault Path | `platform-admin-password` | `master-admin-password` |
| Auth Method | Uses master admin to authenticate | Uses current master admin |

## Security Principles

Both scripts follow the same security principles:
- ✅ No environment variables for passwords
- ✅ Direct Vault access via Docker exec
- ✅ Passwords retrieved securely from Vault
- ✅ Idempotent (can run multiple times safely)

## Notes

- Master admin password might already be changed from default
- Script tries default password first, then Vault password
- If already synced, script detects and exits gracefully
- Master admin password changes require re-authentication for future operations

## Troubleshooting

If authentication fails:
1. Check if Keycloak is running: `docker ps | grep keycloak`
2. Check if Vault is running: `docker ps | grep vault`
3. Verify master admin password in Vault:
   ```bash
   docker exec -e VAULT_ADDR='http://127.0.0.1:8200' -e VAULT_TOKEN='sentinelgrid-dev-root-token' vault vault kv get sentinelgrid/keycloak/master-admin-password
   ```

