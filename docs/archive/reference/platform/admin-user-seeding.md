# Admin User Seeding Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Overview

This guide explains how to seed the default admin user for SentinelGrid development and testing.

## Default Admin User

- **Email**: `admin@sentinelgrid.ai`
- **Password**: `admin123`
- **Role**: `TENANT_ADMIN`
- **Tenant**: `sentinelgrid` (default tenant)

## What Gets Created

The seed script creates:

1. **Default Tenant** (`sentinelgrid`) in the database
2. **Keycloak Realm** (`sentinelgrid`) if it doesn't exist
3. **Keycloak Clients**:
   - `sentinelgrid-web` (public client for frontend)
   - `sentinelgrid-api` (confidential client for backend)
4. **Roles**: TENANT_ADMIN, SOC_MANAGER, SOC_ANALYST, VIEW_ONLY
5. **Protocol Mapper**: `tenant_id` mapper for API client
6. **Admin User**: `admin@sentinelgrid.ai` with password `admin123`

## Running the Seed Script

### Prerequisites

1. Keycloak is running and accessible
2. Database is running and accessible
3. Keycloak admin credentials are available

### Option 1: Direct Execution

```bash
cd /path/to/SentinelGrid
python backend/scripts/seed_admin_user.py
```

### Option 2: With Environment Variables

```bash
export KEYCLOAK_URL="http://localhost:8081"
export KEYCLOAK_ADMIN_USER="admin"
export KEYCLOAK_ADMIN_PASSWORD="admin"
export DB_URL="postgresql://sg:sg@localhost:5432/sg"

python backend/scripts/seed_admin_user.py
```

### Option 3: Via Docker

```bash
docker-compose exec iam_agent python /app/scripts/seed_admin_user.py
```

## Verification

### 1. Check Database

```sql
SELECT id, name, slug, status FROM tenants WHERE slug = 'sentinelgrid';
```

Should return the default tenant.

### 2. Check Keycloak Realm

```bash
curl http://localhost:8081/realms/sentinelgrid \
  -H "Authorization: Bearer <admin-token>"
```

### 3. Test Login

```bash
curl -X POST http://localhost:8081/realms/sentinelgrid/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=sentinelgrid-web" \
  -d "username=admin@sentinelgrid.ai" \
  -d "password=admin123" \
  -d "grant_type=password" \
  -d "scope=openid profile email"
```

Should return an `access_token`.

### 4. Test Frontend Login

1. Navigate to http://localhost:3000
2. Click "Sign in"
3. Enter credentials:
   - Email: `admin@sentinelgrid.ai`
   - Password: `admin123`
4. Should redirect to `/dashboard`

## Login Flow

1. User clicks "Sign in" → Redirects to Keycloak login
2. User enters credentials → Keycloak authenticates
3. Keycloak redirects to `/auth/callback?code=...`
4. Frontend exchanges code for token
5. Frontend stores token and user info in localStorage
6. Frontend redirects to `/dashboard`

## Troubleshooting

### User Already Exists

If the user already exists, the script will:
- Update the user's password to `admin123`
- Update tenant_id attribute
- Ensure TENANT_ADMIN role is assigned

### Realm Already Exists

If the realm already exists, the script will:
- Skip realm creation
- Continue with client/user creation
- Update existing configurations if needed

### Connection Errors

If you see connection errors:

1. **Keycloak not running**:
   ```bash
   docker-compose ps keycloak
   ```

2. **Wrong Keycloak URL**:
   ```bash
   export KEYCLOAK_URL="http://localhost:8081"  # or your Keycloak URL
   ```

3. **Wrong admin credentials**:
   ```bash
   export KEYCLOAK_ADMIN_USER="admin"
   export KEYCLOAK_ADMIN_PASSWORD="admin"  # or your admin password
   ```

### Database Errors

If you see database errors:

1. **Database not running**:
   ```bash
   docker-compose ps postgres
   ```

2. **Wrong database URL**:
   ```bash
   export DB_URL="postgresql://sg:sg@localhost:5432/sg"
   ```

3. **Tables not created**:
   ```bash
   # Run migrations first
   psql -U sg -d sg -f backend/migrations/001_initial_schema.sql
   ```

## Security Notes

⚠️ **Important**: The default password `admin123` is for development only!

For production:
1. Change the admin password immediately
2. Use strong, unique passwords
3. Enable MFA for admin accounts
4. Rotate passwords regularly

## Integration with Docker Compose

Add to `docker-compose.dev.yml`:

```yaml
seed_admin:
  build:
    context: ./backend
    dockerfile: services/iam_agent/Dockerfile
  command: python /app/scripts/seed_admin_user.py
  environment:
    - KEYCLOAK_URL=http://keycloak:8080
    - KEYCLOAK_ADMIN_USER=admin
    - KEYCLOAK_ADMIN_PASSWORD=admin
    - DB_URL=postgresql://sg:sg@postgres:5432/sg
  depends_on:
    - keycloak
    - postgres
  profiles:
    - seed
```

Then run:
```bash
docker-compose --profile seed up seed_admin
```

## Next Steps

After seeding:

1. **Test Login**: Verify you can log in at http://localhost:3000
2. **Check Dashboard**: Ensure dashboard loads correctly
3. **Verify Permissions**: Check that admin user has TENANT_ADMIN role
4. **Create Additional Users**: Use the UI or API to create more users

## Related Files

- `backend/scripts/seed_admin_user.py` - Seed script
- `frontend/src/app/auth/callback/page.tsx` - OAuth callback handler
- `frontend/src/lib/providers/AuthProvider.tsx` - Auth context provider
- `backend/services/iam_agent/app/services/keycloak_client.py` - Keycloak client

