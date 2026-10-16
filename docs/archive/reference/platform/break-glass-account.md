# Break-Glass Account

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Purpose:** Emergency super admin account for Keycloak access when normal authentication fails.

## Account Details

**Username:** `break-glass-admin`  
**Realm:** `master`  
**Password:** `BreakGlass2024!ChangeMe` (default - **MUST BE CHANGED IN PRODUCTION**)  
**Email:** `break-glass@sentinelgrid.local`  
**Privileges:** Full admin access (admin role in master realm)

## Configuration

The break-glass account is automatically created by the IAM Agent seeder on startup.

### Environment Variables

You can customize the break-glass account via environment variables:

```bash
KEYCLOAK_BREAK_GLASS_USER=break-glass-admin
KEYCLOAK_BREAK_GLASS_PASSWORD=BreakGlass2024!ChangeMe
KEYCLOAK_BREAK_GLASS_EMAIL=break-glass@sentinelgrid.local
```

## Security Best Practices

1. **Change Default Password**: Immediately change the password in production
2. **Store Securely**: Store credentials in secure secret management (AWS Secrets Manager, HashiCorp Vault, etc.)
3. **Access Logging**: All break-glass account access should be logged and monitored
4. **Use Sparingly**: Only use when normal service account authentication fails
5. **Rotate Regularly**: Rotate the password on a regular schedule
6. **Document Usage**: Document any usage of the break-glass account

## Usage

### Via Keycloak Admin Console

1. Access: http://localhost:8081/admin
2. Login with break-glass credentials
3. Full admin access to all realms

### Via kcadm.sh

```bash
docker-compose exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 \
  --realm master \
  --user break-glass-admin \
  --password BreakGlass2024!ChangeMe
```

## Production Checklist

- [ ] Change default password
- [ ] Store credentials in secure secret management
- [ ] Set up access logging and alerting
- [ ] Document break-glass procedure
- [ ] Test break-glass access
- [ ] Set up password rotation schedule

## Related Documents

- `docs/PRODUCTION_READINESS_TODO.md` - Production checklist
- `docs/archive/reference/identity/keycloak-service-account-migration.md` - Service account setup

