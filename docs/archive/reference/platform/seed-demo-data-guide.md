# Demo Data Seeding Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


This guide explains how to run the `seed_demo_data.py` script to populate Keycloak and the database with NimbusEdge Technologies demo data.

## Prerequisites

### 1. Services Must Be Running

The following services need to be running before seeding:

```bash
# Check if services are running
docker-compose -f docker-compose.dev.yml ps

# Start required services if not running
docker-compose -f docker-compose.dev.yml up -d keycloak postgres
```

**Required Services:**
- ✅ **PostgreSQL** - Database for assets, apps, alerts, etc.
- ✅ **Keycloak** - Identity provider for users and authentication

**Optional (for full demo):**
- Redis (for caching)
- API Gateway (for API access)
- Frontend (for UI)

### 2. Database Migrations Must Be Applied

All required database tables must exist. The script uses these tables:

- `tenants` - Tenant information
- `assets` - Hardware/software inventory (CMDB)
- `apps` - Integrated applications
- `entitlements` - App permissions
- `user_entitlements` - User-to-app mappings
- `access_profiles` - Access profile bundles
- `alerts` - Security alerts
- `alert_ai_analysis` - AI analysis of alerts

**Check if migrations are applied:**

```bash
# Connect to database
docker-compose -f docker-compose.dev.yml exec postgres psql -U sg -d sg

# Check if key tables exist
\dt tenants
\dt assets
\dt apps
\dt entitlements
\dt user_entitlements
```

**Apply migrations if needed:**

The migrations are in `backend/migrations/`. Key migrations needed:
- `001_initial_schema.sql` - Base schema (tenants, alerts, etc.)
- `003_vulnerabilities_cmdb.sql` - Assets table
- `015_iam_portal_schema.sql` - Apps, entitlements, access profiles

You can run migrations manually or use `init_complete_stack.sh` which applies all migrations.

### 3. Python Dependencies Must Be Installed

The script requires these Python packages:

```bash
# Install dependencies
pip install sqlalchemy psycopg2-binary python-keycloak

# Or if using the project's requirements
pip install -r backend/libs/requirements.txt
pip install python-keycloak  # Additional dependency
```

**Required packages:**
- `sqlalchemy` - Database ORM
- `psycopg2-binary` - PostgreSQL driver
- `python-keycloak` - Keycloak Admin API client

### 4. Keycloak Must Be Accessible

Keycloak should be:
- Running and healthy
- Accessible at the configured URL (default: `http://localhost:8081`)
- Master admin credentials available (default: `admin`/`admin`)

**Verify Keycloak:**

```bash
# Check if Keycloak is running
curl http://localhost:8081/health/ready

# Or check via Docker
docker-compose -f docker-compose.dev.yml ps keycloak
```

## Configuration

The script uses environment variables (with defaults):

```bash
# Keycloak Configuration
KEYCLOAK_URL=http://localhost:8081          # Keycloak URL
KEYCLOAK_ADMIN_USER=admin                   # Master admin username
KEYCLOAK_ADMIN_PASSWORD=admin               # Master admin password

# Database Configuration
DB_URL=postgresql://sg:sg@localhost:5432/sg  # PostgreSQL connection string

# Demo Tenant Configuration
TENANT_NAME="Demo Company"                   # Tenant display name
TENANT_SLUG=demo                             # Tenant slug
REALM_NAME=demo                              # Keycloak realm name

# Optional
SKIP_KEYCLOAK=false                          # Skip Keycloak setup if true
```

**Default values work if:**
- Keycloak is at `http://localhost:8081` with default `admin`/`admin` credentials
- PostgreSQL is at `localhost:5432` with user `sg`/password `sg`/database `sg`
- You're creating a demo tenant/realm

## Running the Script

### Basic Usage

```bash
# From project root
python backend/scripts/seed_demo_data.py
```

### With Custom Configuration

```bash
# Set environment variables
export KEYCLOAK_URL=http://localhost:8081
export KEYCLOAK_ADMIN_USER=admin
export KEYCLOAK_ADMIN_PASSWORD=admin
export DB_URL=postgresql://sg:sg@localhost:5432/sg
export TENANT_NAME="NimbusEdge Technologies"
export TENANT_SLUG=demo
export REALM_NAME=demo

# Run script
python backend/scripts/seed_demo_data.py
```

### Database-Only Mode (Skip Keycloak)

If Keycloak is not available, you can seed database tables only:

```bash
SKIP_KEYCLOAK=true python backend/scripts/seed_demo_data.py
```

**Note:** This will skip:
- Keycloak realm creation
- User creation in Keycloak
- NimbusEdge employee creation (requires Keycloak)

But will still create:
- Database apps
- Access profiles
- Security alerts

## What Gets Created

### 1. Keycloak Realm (`demo`)

- **Realm:** `demo`
- **Display Name:** "Demo Company" (or configured `TENANT_NAME`)
- **Settings:** Email login enabled, brute force protection, SSO configured

### 2. Keycloak Clients

- **Web Client:** `demo-web`
  - Public client for frontend login
  - Redirect URIs: `http://localhost:3000/*`, `https://localhost:3443/*`
- **API Client:** `demo-api`
  - Confidential client for service-to-service auth
  - Service accounts enabled

### 3. Keycloak Roles

- `TENANT_ADMIN` - Full tenant access
- `SOC_MANAGER` - SOC management access
- `SOC_ANALYST` - Analyst access
- `VIEW_ONLY` - Read-only access

### 4. Demo Users (Existing)

- `admin@demo.sentinelgrid.ai` - Tenant admin
- `soc.manager@demo.sentinelgrid.ai` - SOC manager
- `analyst1@demo.sentinelgrid.ai` - SOC analyst
- `analyst2@demo.sentinelgrid.ai` - SOC analyst
- `viewer@demo.sentinelgrid.ai` - View-only user

**Password for all demo users:** `DemoPassword123!`

### 5. NimbusEdge Employees (New)

Five employees from NimbusEdge Technologies:

1. **Ava Thompson** (`ava.thompson@demo.sentinelgrid.ai`)
   - Role: CEO / Founder
   - Department: Executive
   - Keycloak Role: TENANT_ADMIN
   - Apps: Google Workspace, Slack, Notion, Zoom

2. **Leo Martinez** (`leo.martinez@demo.sentinelgrid.ai`)
   - Role: CTO
   - Department: Engineering
   - Keycloak Role: SOC_MANAGER
   - Apps: Google Workspace, Slack, Notion, GitHub, Jira, Zoom

3. **Priya Shah** (`priya.shah@demo.sentinelgrid.ai`)
   - Role: Lead Software Engineer
   - Department: Engineering
   - Keycloak Role: SOC_ANALYST
   - Apps: Google Workspace, Slack, Notion, GitHub, Jira

4. **Marcus Reed** (`marcus.reed@demo.sentinelgrid.ai`)
   - Role: Product Manager
   - Department: Product
   - Keycloak Role: SOC_ANALYST
   - Apps: Google Workspace, Slack, Notion, Jira, GitHub (read-only), Zoom

5. **Sara Delgado** (`sara.delgado@demo.sentinelgrid.ai`)
   - Role: Operations & HR
   - Department: Operations
   - Keycloak Role: SOC_ANALYST
   - Apps: Google Workspace, Slack, Notion, Zoom

**Password for all NimbusEdge employees:** `DemoPassword123!`

### 6. Apps in Database

- SentinelGrid
- GitHub
- AWS Console
- Jira
- Slack
- Microsoft 365
- Salesforce
- Confluence
- **Google Workspace** (new)
- **Notion** (new)
- **Zoom** (new)

### 7. Assets (Devices) in Database

Ten company-issued devices (2 per employee):

**Ava Thompson:**
- MacBook Pro 14" (M3 Pro) - Serial: MBP14-A001
- iPhone 15 Pro - Serial: IP15P-A001

**Leo Martinez:**
- MacBook Pro 16" (M3 Max) - Serial: MBP16-L001
- Pixel 8 Pro - Serial: PIX8P-L001

**Priya Shah:**
- MacBook Air 15" (M3) - Serial: MBA15-P001
- iPhone 14 - Serial: IP14-P001

**Marcus Reed:**
- MacBook Air 13" (M2) - Serial: MBA13-M001
- Samsung Galaxy S23 - Serial: SG23-M001

**Sara Delgado:**
- Surface Laptop 5 (Windows 11) - Serial: SL5-S001
- iPhone 13 - Serial: IP13-S001

All devices stored in `assets` table with:
- Device type (workstation/mobile)
- Manufacturer and model
- Operating system
- Serial number
- Owner (employee email)
- Department
- Hardware specs (JSONB metadata)

### 8. App Access Mappings

Each employee is mapped to their apps via `user_entitlements`:

- Entitlements created: `{app_name}_access` for each app
- Special case: `github_read_only` for Marcus Reed
- User-entitlement links created in `user_entitlements` table

### 9. Security Alerts

Seven demo security alerts with AI analysis:
- Ransomware activity
- Phishing attempts
- Brute force attacks
- IAM policy changes
- Malware detection
- Data exposure
- Credential dumping

### 10. Access Profiles

Default access profiles:
- Standard Employee
- Developer
- Manager
- Executive
- Contractor

## Verification

### Check Keycloak

```bash
# Visit Keycloak Admin Console
open http://localhost:8081/admin

# Login with admin/admin
# Select "demo" realm from dropdown
# Go to Users → Verify NimbusEdge employees exist
```

### Check Database

```bash
# Connect to database
docker-compose -f docker-compose.dev.yml exec postgres psql -U sg -d sg

# Check tenant
SELECT id, name, slug FROM tenants WHERE slug = 'demo';

# Check apps
SELECT name, display_name FROM apps WHERE tenant_id = (SELECT id FROM tenants WHERE slug = 'demo');

# Check assets
SELECT name, asset_type, owner, department FROM assets WHERE tenant_id = (SELECT id FROM tenants WHERE slug = 'demo');

# Check user entitlements
SELECT COUNT(*) FROM user_entitlements WHERE tenant_id = (SELECT id FROM tenants WHERE slug = 'demo');
```

### Test Login

```bash
# Test login as NimbusEdge employee
curl -X POST http://localhost:8081/realms/demo/protocol/openid-connect/token \
  -d "grant_type=password" \
  -d "client_id=demo-web" \
  -d "username=ava.thompson@demo.sentinelgrid.ai" \
  -d "password=DemoPassword123!"
```

Should return an access token with `tenant_id` claim.

## Troubleshooting

### Error: "Could not connect to Keycloak"

**Solution:**
- Ensure Keycloak is running: `docker-compose -f docker-compose.dev.yml ps keycloak`
- Check Keycloak URL: `curl http://localhost:8081/health/ready`
- Verify credentials: Default is `admin`/`admin` for dev mode

### Error: "Could not connect to database"

**Solution:**
- Ensure PostgreSQL is running: `docker-compose -f docker-compose.dev.yml ps postgres`
- Check connection string: Default is `postgresql://sg:sg@localhost:5432/sg`
- Test connection: `docker-compose -f docker-compose.dev.yml exec postgres psql -U sg -d sg -c "SELECT 1;"`

### Error: "Table does not exist"

**Solution:**
- Migrations not applied: Run `backend/scripts/init_complete_stack.sh` or apply migrations manually
- Check which migrations are needed: Review `backend/migrations/` directory

### Error: "python-keycloak not installed"

**Solution:**
```bash
pip install python-keycloak
```

### Error: "Realm already exists"

**Solution:**
- This is fine - script is idempotent and will update existing realm/users
- If you want a fresh start, delete the realm in Keycloak admin console first

### Keycloak Users Created But Can't Login

**Check:**
- Password is set: `DemoPassword123!`
- User is enabled
- Required actions are cleared
- Email is verified
- Realm is correct (`demo`)

## Next Steps

After seeding:

1. **Test Login** - Log in as one of the NimbusEdge employees
2. **View Assets** - Check the assets/inventory page to see devices
3. **View Apps** - Check the IAM portal to see app access
4. **View Alerts** - Check the alerts page to see security alerts
5. **Demo to Customers** - Use the demo credentials for customer demonstrations

## Cleanup

To remove demo data:

```bash
# Remove Keycloak realm (via admin console or API)
# Delete tenant from database:
docker-compose -f docker-compose.dev.yml exec postgres psql -U sg -d sg -c "DELETE FROM tenants WHERE slug = 'demo';"
```

**Warning:** This will cascade delete all related data (assets, apps, alerts, etc.) due to foreign key constraints.




