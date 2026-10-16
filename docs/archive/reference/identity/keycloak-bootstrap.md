# Keycloak Bootstrap Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This guide explains how to reset and bootstrap Keycloak for SentinelGrid with all necessary configuration, clients, roles, and the admin user.

## Overview

The bootstrap script (`backend/scripts/bootstrap_keycloak.py`) performs the following:

1. **Resets Keycloak database** (optional, with `--reset-db`)
2. **Creates SentinelGrid realm** with proper configuration
3. **Creates clients**:
   - `sentinelgrid-web` - Public client for website
   - `sentinelgrid-frontend` - Public client for dashboard
   - `sentinelgrid-api` - Confidential client for API
   - `sentinelgrid-iam-agent` - Service account client for IAM Agent
4. **Creates roles**:
   - `TENANT_ADMIN` - Full control over tenant
   - `SOC_MANAGER` - Manage incidents, playbooks, team
   - `SOC_ANALYST` - View and triage alerts, manage incidents
   - `VIEW_ONLY` - Read-only access
5. **Creates protocol mapper** - Maps `tenant_id` user attribute to JWT tokens
6. **Creates admin user**: `admin@sentinelgrid.ai` with password `admin123`
7. **Creates default tenant** in PostgreSQL database

## Prerequisites

1. Keycloak container running and accessible
2. PostgreSQL database accessible
3. Python dependencies installed:
   ```bash
   pip install python-keycloak sqlalchemy psycopg2-binary
   ```

## Usage

### Option 1: Full Reset (Recommended for Fresh Start)

This will reset the Keycloak database and bootstrap everything:

```bash
# Reset Keycloak database
python backend/scripts/bootstrap_keycloak.py --reset-db --wait
```

The `--reset-db` flag will:
- Drop the existing Keycloak database
- Create a new empty Keycloak database
- Wait for Keycloak to restart and be ready

### Option 2: Bootstrap Only (No Database Reset)

If you just want to recreate the realm, clients, and users without resetting the database:

```bash
python backend/scripts/bootstrap_keycloak.py
```

This will:
- Delete and recreate the `sentinelgrid` realm
- Create all clients, roles, and mappers
- Create/update the admin user

### Option 3: Manual Database Reset

If you prefer to reset the database manually:

```bash
# Stop Keycloak
docker-compose stop keycloak

# Connect to PostgreSQL and reset
docker-compose exec postgres psql -U keycloak -d postgres -c "DROP DATABASE IF EXISTS keycloak;"
docker-compose exec postgres psql -U keycloak -d postgres -c "CREATE DATABASE keycloak;"

# Restart Keycloak
docker-compose start keycloak

# Wait for Keycloak to be ready, then bootstrap
python backend/scripts/bootstrap_keycloak.py
```

## Environment Variables

You can customize the bootstrap process with environment variables:

```bash
export KEYCLOAK_URL=http://localhost:8081
export KEYCLOAK_ADMIN_USER=admin
export KEYCLOAK_ADMIN_PASSWORD=admin
export DB_URL=postgresql://sg:sg@localhost:5432/sg
export KEYCLOAK_DB_URL=postgresql://keycloak:keycloak@localhost:${EXAMPLE_VALUE}
```

## What Gets Created

### Realm: `sentinelgrid`

- **Display Name**: SentinelGrid
- **Login with Email**: Enabled
- **Duplicate Emails**: Disabled
- **Brute Force Protection**: Enabled
- **Remember Me**: Enabled
- **Access Token Lifespan**: 1 hour
- **SSO Session Idle Timeout**: 30 minutes

### Clients

1. **sentinelgrid-web** (Public)
   - Redirect URIs: `http://localhost:3000/*`, `https://*.sentinelgrid.com/*`
   - Web Origins: `+` (all)
   - Used by: Marketing website

2. **sentinelgrid-frontend** (Public)
   - Redirect URIs: `http://localhost:3000/*`, `http://localhost:3001/*`
   - Web Origins: `+` (all)
   - Used by: Dashboard frontend

3. **sentinelgrid-api** (Confidential)
   - Service account: Disabled
   - Used by: Backend API services
   - Has `tenant_id` protocol mapper

4. **sentinelgrid-iam-agent** (Confidential)
   - Service account: Enabled
   - Used by: IAM Agent service

### Roles

- `TENANT_ADMIN` - Full control over tenant
- `SOC_MANAGER` - Manage incidents, playbooks, team
- `SOC_ANALYST` - View and triage alerts, manage incidents
- `VIEW_ONLY` - Read-only access

### Admin User

- **Email**: `admin@sentinelgrid.ai`
- **Password**: `admin123`
- **Role**: `TENANT_ADMIN`
- **Tenant ID**: Auto-assigned from database

### Protocol Mapper

- **Name**: `tenant-id-mapper`
- **Type**: User Attribute Mapper
- **User Attribute**: `tenant_id`
- **Token Claim**: `tenant_id`
- **Added to**: ID token and Access token

## Verification

After running the bootstrap script, verify everything is set up correctly:

```bash
# Check Keycloak is running
curl http://localhost:8081/health/ready

# Check realm exists
curl http://localhost:8081/realms/sentinelgrid

# Test login (should redirect to Keycloak)
curl -L http://localhost:3000/login
```

## Troubleshooting

### Keycloak Not Ready

If you see "Keycloak may not be fully ready", wait a bit longer and try again:

```bash
# Check Keycloak logs
docker logs sentinelgrid-keycloak-1

# Wait for Keycloak to be ready
curl http://localhost:8081/health/ready
```

### Database Connection Error

If you get database connection errors:

1. Check PostgreSQL is running:
   ```bash
   docker ps | grep postgres
   ```

2. Verify database credentials in environment variables

3. Check Keycloak database exists:
   ```bash
   docker-compose exec postgres psql -U keycloak -d postgres -c "\l" | grep keycloak
   ```

### Realm Already Exists Error

The script will automatically delete and recreate the realm. If you see persistent errors:

1. Manually delete the realm via Keycloak admin console
2. Or reset the database with `--reset-db`

## Integration with Docker Compose

You can add the bootstrap script to your docker-compose setup:

```yaml
keycloak_bootstrap:
  build:
    context: ./backend
    dockerfile: services/keycloak_bootstrap/Dockerfile
  environment:
    - KEYCLOAK_URL=http://keycloak:8080
    - KEYCLOAK_ADMIN_USER=admin
    - KEYCLOAK_ADMIN_PASSWORD=${KEYCLOAK_ADMIN_PASSWORD:-admin}
    - DB_URL=postgresql://sg:sg@postgres:5432/sg
    - KEYCLOAK_DB_URL=postgresql://keycloak:keycloak@keycloak_db:${EXAMPLE_VALUE}
  depends_on:
    keycloak:
      condition: service_healthy
    postgres:
      condition: service_healthy
  command: python scripts/bootstrap_keycloak.py --wait
```

## Next Steps

After bootstrapping:

1. **Test Login**: Go to http://localhost:3000 and click "Sign in"
2. **Verify Admin User**: Log in with `admin@sentinelgrid.ai` / `admin123`
3. **Check Dashboard**: You should be redirected to the dashboard
4. **Verify Tenant**: Check that the user has the correct `tenant_id` in their token

## Maintenance

To update the bootstrap configuration:

1. Edit `backend/scripts/bootstrap_keycloak.py`
2. Run the bootstrap script again (it will update existing resources)
3. Or use `--reset-db` for a complete reset

