# Keycloak Password Sync from Vault

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This document explains how Keycloak passwords are synced from Vault, without using environment variables for security.

## Overview

Both platform admin and master admin passwords are stored in Vault and synced to Keycloak:
- **Platform Admin**: `admin@sentinelgrid.ai` in `sg-admin` realm
- **Master Admin**: `admin` in `master` realm

## Password Storage in Vault

```
sentinelgrid/keycloak/platform-admin-password  → Platform admin password
sentinelgrid/keycloak/master-admin-password    → Master admin password
```

## Sync Scripts

### Platform Admin Password Sync

**Python Script:**
```bash
python backend/scripts/update_platform_admin_password.py
```

**Bash Script:**
```bash
backend/scripts/sync_keycloak_password_simple.sh
```

**What it does:**
1. Retrieves password from Vault (`sentinelgrid/keycloak/platform-admin-password`)
2. Connects to Keycloak using master admin credentials (tries default, then Vault)
3. Updates password for `admin@sentinelgrid.ai` in `sg-admin` realm

### Master Admin Password Sync

**Python Script:**
```bash
python backend/scripts/update_master_admin_password.py
```

**Bash Script:**
```bash
backend/scripts/sync_master_admin_password_simple.sh
```

**What it does:**
1. Retrieves password from Vault (`sentinelgrid/keycloak/master-admin-password`)
2. Connects to Keycloak using current master admin password (tries default, then Vault)
3. Updates password for `admin` in `master` realm

## How It Works

### Security Principles

1. **No Environment Variables**: Passwords are never passed via environment variables
2. **Vault as Source of Truth**: All passwords stored securely in Vault
3. **Direct Vault Access**: Scripts use `docker exec` to access Vault directly
4. **Idempotent**: Scripts can be run multiple times safely

### Authentication Flow

1. **Get password from Vault** using `docker exec vault vault kv get ...`
2. **Connect to Keycloak** using:
   - Try default password first (`admin`/`admin` for dev mode)
   - Fallback to Vault password if default doesn't work
3. **Update password** using Keycloak Admin API or `kcadm.sh`

### Python Script Pattern

```python
def get_vault_secret(path: str, field: str = "value") -> str:
    """Fetch a secret from Vault using docker exec."""
    result = subprocess.run([
        "docker", "exec",
        "-e", f"VAULT_ADDR={vault_addr}",
        "-e", f"VAULT_TOKEN={vault_token}",
        "vault",
        "vault", "kv", "get", "-field", field, path
    ], ...)
    return result.stdout.strip()
```

### Bash Script Pattern

```bash
PASSWORD=$(docker exec -e VAULT_ADDR='http://127.0.0.1:8200' \
    -e VAULT_TOKEN='sentinelgrid-dev-root-token' \
    vault vault kv get -field=value sentinelgrid/keycloak/platform-admin-password)
```

## Usage Examples

### Sync Platform Admin Password

```bash
# Using Python script
python backend/scripts/update_platform_admin_password.py

# Using bash script
backend/scripts/sync_keycloak_password_simple.sh
```

### Sync Master Admin Password

```bash
# Using Python script
python backend/scripts/update_master_admin_password.py

# Using bash script
backend/scripts/sync_master_admin_password_simple.sh
```

## When to Run

Run these scripts when:
1. **Vault is re-seeded**: After Vault loses data (dev mode) and is re-initialized
2. **Password rotation**: When passwords are rotated in Vault
3. **New deployment**: After setting up Keycloak for the first time
4. **Password mismatch**: When Keycloak password doesn't match Vault

## Troubleshooting

### Error: "Failed to retrieve password from Vault"

**Solution:**
```bash
# Check if Vault is running
docker ps | grep vault

# Re-initialize Vault if needed
backend/scripts/init_vault.sh
```

### Error: "Failed to connect to Keycloak"

**Solution:**
```bash
# Check if Keycloak is running
docker ps | grep keycloak

# Check Keycloak logs
docker logs sentinelgrid-keycloak-1
```

### Error: "User not found in realm"

**Solution:**
```bash
# Create realms first
python backend/scripts/seed_realms.py
```

## Key Differences: Platform Admin vs Master Admin

| Aspect | Platform Admin | Master Admin |
|--------|----------------|--------------|
| Realm | `sg-admin` | `master` |
| Username | `admin@sentinelgrid.ai` | `admin` |
| Vault Path | `platform-admin-password` | `master-admin-password` |
| Purpose | Platform administration | Keycloak administration |
| Default Password | None | `admin` (dev mode) |

## Security Notes

- ✅ Passwords are retrieved from Vault (secure storage)
- ✅ No passwords in environment variables
- ✅ No passwords in command line arguments
- ✅ Direct Vault access via Docker exec
- ⚠️ Vault dev mode: Passwords lost on restart
- ⚠️ For production: Use persistent Vault storage

