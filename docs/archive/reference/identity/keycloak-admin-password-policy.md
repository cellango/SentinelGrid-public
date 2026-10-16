# Keycloak Admin Password Policy

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Status:** Active Policy  
**Date:** 2025-12-05

---

## Policy

**In development environments, the Keycloak master realm admin password MUST remain the default `admin` password.**

### Rules

1. **Never change admin password in dev**
   - Seed scripts must NOT change the master admin password in dev
   - Only change password in production (`ENVIRONMENT=production`)

2. **Environment variable protection**
   - `KEYCLOAK_ADMIN_PASSWORD` defaults to `admin` in `docker-compose.dev.yml`
   - Do NOT override this in dev environments

3. **Seed script protection**
   - `backend/scripts/seed_realms.py` has guards to prevent password changes in dev
   - Checks `ENVIRONMENT` or `PRODUCTION` env vars before changing password

---

## Implementation

### Seed Script Protection

The `seed_realms.py` script includes environment checks:

```python
environment = os.getenv("ENVIRONMENT", "development").lower()
is_production = environment == "production" or os.getenv("PRODUCTION", "false").lower() == "true"

if is_production and new_admin_password and new_admin_password != admin_password:
    # Only change password in production
    change_master_admin_password(client, new_admin_password)
elif not is_production:
    logger.info("⏭️  Skipping master admin password change (dev environment - keeping default 'admin' password)")
```

### Docker Compose Configuration

```yaml
keycloak:
  environment:
    - KEYCLOAK_ADMIN=admin
    - KEYCLOAK_ADMIN_PASSWORD=${KEYCLOAK_ADMIN_PASSWORD:-admin}  # Defaults to 'admin'
```

---

## Password Policy

### Master Realm
- **Current:** No password policy (Keycloak default)
- **Recommendation:** Set policy for production: `length(12) and digits(1) and lowerCase(1) and upperCase(1) and specialChars(1)`

### Customer Realms
- **Policy:** `length(8) and digits(1) and lowerCase(1) and upperCase(1) and notUsername`
- **Example compliant passwords:** `Admin123!`, `Test1234`, `ChangeMe123!`

---

## Troubleshooting

### If Admin Password Gets Changed

1. **Option 1: Reset Keycloak Database (Clean)**
   ```bash
   ./scripts/reset-keycloak-clean.sh
   ```
   - Backs up existing data
   - Removes Keycloak database
   - Starts fresh with admin/admin

2. **Option 2: Manual Reset via Admin Console**
   - Access http://localhost:8080/admin
   - If you can log in, reset password via UI
   - If you can't log in, use Option 1

### Prevention

- ✅ Seed scripts check environment before changing password
- ✅ Docker Compose defaults to `admin` password
- ✅ Documentation warns against changing password in dev
- ⚠️  Consider adding CI/CD checks to prevent password changes in dev

---

## Production

In production:
- Set `ENVIRONMENT=production` or `PRODUCTION=true`
- Use strong password from Vault
- Seed scripts will change password to Vault value
- Master realm should have password policy set

---

## Related Files

- `backend/scripts/seed_realms.py` - Main seed script with password change logic
- `docker-compose.dev.yml` - Keycloak configuration
- `scripts/reset-keycloak-clean.sh` - Clean reset script
- `scripts/backup-keycloak-realms.sh` - Backup script

