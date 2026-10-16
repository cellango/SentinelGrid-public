# Keycloak Bootstrap Scripts

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


## Quick Start

### Full Reset and Bootstrap

```bash
# Reset Keycloak database and bootstrap everything
python backend/scripts/bootstrap_keycloak.py --reset-db --wait
```

### Bootstrap Only (No Database Reset)

```bash
# Just recreate realm, clients, and users
python backend/scripts/bootstrap_keycloak.py
```

## What It Does

1. **Resets Keycloak database** (optional with `--reset-db`)
2. **Creates SentinelGrid realm**
3. **Creates 4 clients**: web, frontend, api, iam-agent
4. **Creates 4 roles**: TENANT_ADMIN, SOC_MANAGER, SOC_ANALYST, VIEW_ONLY
5. **Creates protocol mapper** for `tenant_id`
6. **Creates admin user**: `admin@sentinelgrid.ai` / `admin123`
7. **Creates default tenant** in PostgreSQL

## Requirements

```bash
pip install python-keycloak sqlalchemy psycopg2-binary requests
```

## Environment Variables

```bash
export KEYCLOAK_URL=http://localhost:8081
export KEYCLOAK_ADMIN_USER=admin
export KEYCLOAK_ADMIN_PASSWORD=admin
export DB_URL=postgresql://sg:sg@localhost:5432/sg
export KEYCLOAK_DB_URL=postgresql://keycloak:keycloak@localhost:5432/keycloak
```

## See Also

- Full documentation: `docs/archive/reference/identity/keycloak-bootstrap.md`
- Original seed script: `backend/scripts/seed_admin_user.py`

