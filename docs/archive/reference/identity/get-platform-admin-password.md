# How to Get the Platform Admin Password

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Quick Answer: Password Rotation

**The platform admin password does NOT automatically rotate.** It's stored in Vault and only changes when manually updated.

## Current Password Location

The password is stored in HashiCorp Vault at:
- **Path:** `sentinelgrid/keycloak/platform-admin-password`

## How to Retrieve the Current Password

### Option 1: Using Docker (if Vault container is running)

```bash
# Get password from Vault
docker exec -e VAULT_TOKEN='sentinelgrid-dev-root-token' vault \
  vault kv get -field=value sentinelgrid/keycloak/platform-admin-password
```

### Option 2: Using Python Helper

```python
from backend.tests.helpers.vault_helper import get_platform_admin_password

password = get_platform_admin_password()
print(f"Password: {password}")
```

### Option 3: Direct Vault Access

```bash
export VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_TOKEN="sentinelgrid-dev-root-token"
vault kv get -field=value sentinelgrid/keycloak/platform-admin-password
```

## Login Credentials

- **Email:** `admin@sentinelgrid.ai`
- **Realm:** `sg-admin` (platform administration realm)
- **Password:** Retrieved from Vault (see above)

## If Password Doesn't Work

If the password from Vault doesn't work, there may be a mismatch between Vault and Keycloak:

1. **Reset password in Keycloak:**
   - Use Keycloak Admin Console
   - Or use Keycloak Admin API
   - Then update Vault to match

2. **Update password in Vault to match Keycloak:**
   ```bash
   docker exec -e VAULT_TOKEN='sentinelgrid-dev-root-token' vault \
     vault kv put sentinelgrid/keycloak/platform-admin-password value="NEW_PASSWORD"
   ```

## For Demo Realm Testing

If you're testing the demo realm user creation (as requested), use:

- **Email:** `admin@demo.sentinelgrid.ai`
- **Password:** `DemoPassword123!`
- **Realm:** `demo`

This is a simple, shareable password that doesn't rotate.

