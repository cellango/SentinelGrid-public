# SentinelGrid Backend Scripts

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This directory contains scripts for managing SentinelGrid infrastructure, including realm initialization, seeding, and maintenance.

---

## Realm Architecture Scripts

### `init_realm_architecture.sh`

**Purpose:** One-command initialization of the complete realm architecture.

**What it does:**
1. Runs database migration (`002_realm_architecture.sql`)
2. Seeds initial realms in Keycloak and database
3. Verifies setup

**Usage:**
```bash
# With default settings (localhost)
bash backend/scripts/init_realm_architecture.sh

# With custom settings
DB_URL=postgresql://sg:sg@db.example.com:5432/sg \
KEYCLOAK_URL=https://keycloak.example.com \
KEYCLOAK_ADMIN_USER=admin \
KEYCLOAK_ADMIN_PASSWORD=secret \
bash backend/scripts/init_realm_architecture.sh
```

**Prerequisites:**
- PostgreSQL running and accessible
- Keycloak running and accessible
- Python 3.8+ with required packages

**Output:**
```
========================================
  SentinelGrid Realm Architecture Init
========================================

[1/4] Checking prerequisites...
✅ PostgreSQL is accessible
✅ Keycloak is accessible

[2/4] Running database migration...
✅ Database migration completed successfully

[3/4] Seeding realms...
✅ Realms seeded successfully

[4/4] Verifying setup...
✅ Database: Found 3 realms
✅ Table 'customers' exists
✅ Table 'organizations' exists
...

========================================
  ✅ Realm Architecture Initialized!
========================================
```

---

### `seed_realms.py`

**Purpose:** Create and configure initial Keycloak realms.

**What it creates:**
- `sg-admin` - Platform admin realm
- `sg-mt-us-1` - US multi-tenant realm
- `sg-mt-eu-1` - EU multi-tenant realm

**Usage:**
```bash
# Basic usage
python3 backend/scripts/seed_realms.py

# With custom Keycloak
python3 backend/scripts/seed_realms.py \
  --keycloak-url https://keycloak.example.com \
  --admin-user admin \
  --admin-password secret

# With custom database
python3 backend/scripts/seed_realms.py \
  --db-url postgresql://user:pass@host:5432/db
```

**Arguments:**
- `--keycloak-url` - Keycloak server URL (default: https://localhost:8443)
- `--admin-user` - Keycloak admin username (default: admin)
- `--admin-password` - Keycloak admin password (default: admin)
- `--db-url` - PostgreSQL connection URL (default: postgresql://sg:sg@localhost:5432/sg)

**What it configures:**
- Realm settings (password policies, session timeouts, etc.)
- Clients (web, api, iam-agent)
- Roles (TENANT_ADMIN, SOC_MANAGER, SOC_ANALYST, VIEW_ONLY)
- Protocol mappers (sg.tenant_id, sg.tenant_slug, etc.)
- Client scopes (sentinelgrid-tenant)

---

## Database Migration Scripts

### Running Migrations Manually

**Apply a specific migration:**
```bash
psql $DB_URL -f backend/migrations/002_realm_architecture.sql
```

**Check migration status:**
```sql
-- List all tables
\dt

-- Check if realm architecture tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_name IN ('realms', 'customers', 'organizations');

-- Check realm records
SELECT * FROM realms;
```

---

## Testing Scripts

### Test Signup Flow

```bash
# Test signup API
curl -X POST http://localhost:8008/api/v1/signup \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Company",
    "employee_count": 50,
    "admin_email": "admin@test.com",
    "admin_password": "TestPass123!",
    "admin_first_name": "Test",
    "admin_last_name": "User",
    "terms_accepted": true,
    "privacy_accepted": true
  }'
```

### Test Region Detection

```bash
curl http://localhost:8008/api/v1/signup/detect-region
```

### Test Slug Availability

```bash
curl http://localhost:8008/api/v1/signup/check-availability/acme
```

---

## Maintenance Scripts

### Check Realm Capacity

```sql
-- View realm status
SELECT * FROM realm_status
WHERE realm_type = 'multi_tenant'
ORDER BY utilization_percent DESC;

-- Check capacity history
SELECT *
FROM realm_capacity_history
WHERE realm_name = 'sg-mt-us-1'
ORDER BY recorded_at DESC
LIMIT 10;
```

### Create New Realm Shard

```python
from services.multi_tenant_realm_manager import MultiTenantRealmManager

# Initialize manager
mt_manager = MultiTenantRealmManager(keycloak_admin, db_session)

# Create new shard
realm_name = mt_manager.create_multi_tenant_realm(
    realm_name='sg-mt-us-2',
    region='us',
    shard_number=2,
    max_tenants=1000
)
```

### Audit Provisioning Events

```sql
-- Recent provisioning events
SELECT *
FROM tenant_provisioning_log
ORDER BY created_at DESC
LIMIT 100;

-- Failed provisioning attempts
SELECT *
FROM tenant_provisioning_log
WHERE event_type = 'provision_failure'
ORDER BY created_at DESC;

-- Provisioning by realm
SELECT 
    realm_name,
    event_type,
    COUNT(*) as count
FROM tenant_provisioning_log
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY realm_name, event_type
ORDER BY realm_name, event_type;
```

---

## Troubleshooting

### Script Fails with "Cannot connect to PostgreSQL"

**Check:**
1. PostgreSQL is running: `docker ps | grep postgres`
2. Connection string is correct: `echo $DB_URL`
3. Test connection: `psql $DB_URL -c "SELECT 1"`

**Fix:**
```bash
# Start PostgreSQL
docker-compose up -d postgres

# Wait for it to be ready
docker-compose logs -f postgres
```

### Script Fails with "Cannot connect to Keycloak"

**Check:**
1. Keycloak is running: `docker ps | grep keycloak`
2. Keycloak URL is correct: `echo $KEYCLOAK_URL`
3. Test connection: `curl -k $KEYCLOAK_URL/health/ready`

**Fix:**
```bash
# Start Keycloak
docker-compose up -d keycloak

# Wait for it to be ready (takes ~60 seconds)
docker-compose logs -f keycloak
```

### Migration Fails with "Table already exists"

**This is normal if:**
- Migration was partially applied
- Running migration again

**Fix:**
```sql
-- Check what exists
\dt

-- If tables exist but are incomplete, drop and recreate
DROP TABLE IF EXISTS realm_capacity_history CASCADE;
DROP TABLE IF EXISTS tenant_provisioning_log CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS realms CASCADE;

-- Then run migration again
\i backend/migrations/002_realm_architecture.sql
```

### Realm Seeding Fails

**Common causes:**
1. Realm already exists
2. Keycloak admin credentials incorrect
3. Python dependencies missing

**Fix:**
```bash
# Check if realms exist
curl -k -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} \
  https://localhost:8443/admin/realms

# Delete existing realms (if needed)
# WARNING: This deletes all data in the realm!
curl -k -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} -X DELETE \
  https://localhost:8443/admin/realms/sg-admin

# Install Python dependencies
pip install keycloak sqlalchemy psycopg2-binary
```

---

## Environment Variables

### Required

- `DB_URL` - PostgreSQL connection string
- `KEYCLOAK_URL` - Keycloak server URL
- `KEYCLOAK_ADMIN_USER` - Keycloak admin username
- `KEYCLOAK_ADMIN_PASSWORD` - Keycloak admin password

### Optional

- `DEFAULT_MAX_TENANTS_PER_REALM` - Max tenants per multi-tenant realm (default: 1000)
- `REALM_CAPACITY_THRESHOLD` - Utilization threshold for warnings (default: 0.85)
- `DEFAULT_REGION` - Default region if detection fails (default: us)

### Setting Environment Variables

**For single command:**
```bash
DB_URL=postgresql://sg:sg@localhost:5432/sg \
KEYCLOAK_URL=https://localhost:8443 \
bash backend/scripts/init_realm_architecture.sh
```

**For session:**
```bash
export DB_URL=postgresql://sg:sg@localhost:5432/sg
export KEYCLOAK_URL=https://localhost:8443
export KEYCLOAK_ADMIN_USER=admin
export KEYCLOAK_ADMIN_PASSWORD=admin

bash backend/scripts/init_realm_architecture.sh
```

**In docker-compose:**
```yaml
environment:
  - DB_URL=postgresql://sg:sg@postgres:5432/sg
  - KEYCLOAK_URL=https://keycloak:8443
  - KEYCLOAK_ADMIN_USER=admin
  - KEYCLOAK_ADMIN_PASSWORD=admin
```

---

## Quick Start

### First Time Setup

```bash
# 1. Start infrastructure
docker-compose up -d postgres keycloak

# 2. Wait for services to be ready
sleep 60

# 3. Initialize realm architecture
bash backend/scripts/init_realm_architecture.sh

# 4. Verify setup
psql $DB_URL -c "SELECT * FROM realms;"

# 5. Test signup
curl -X POST http://localhost:8008/api/v1/signup \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Corp",
    "employee_count": 50,
    "admin_email": "admin@test.com",
    "admin_password": "TestPass123!",
    "admin_first_name": "Test",
    "admin_last_name": "User",
    "terms_accepted": true,
    "privacy_accepted": true
  }'
```

### Reset Everything

```bash
# WARNING: This deletes all data!

# 1. Drop database tables
psql $DB_URL <<EOF
DROP TABLE IF EXISTS tenant_provisioning_log CASCADE;
DROP TABLE IF EXISTS realm_capacity_history CASCADE;
DROP TABLE IF EXISTS tenants CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS realms CASCADE;
EOF

# 2. Delete Keycloak realms
for realm in sg-admin sg-mt-us-1 sg-mt-eu-1; do
  curl -k -u ${SERVICE_USERNAME}:${SERVICE_PASSWORD} -X DELETE \
    https://localhost:8443/admin/realms/$realm
done

# 3. Re-initialize
bash backend/scripts/init_realm_architecture.sh
```

---

## Additional Resources

- [REALM_ARCHITECTURE_IMPLEMENTATION.md](../../docs/archive/README.md#retired-references) - Complete implementation guide
- [realms.md](../../docs/archive/README.md#retired-references) - Original design document
- `002_realm_architecture.sql` (historical reference unavailable) - Database migration

---

**Last Updated:** December 5, 2025  
**Maintained By:** SentinelGrid Platform Team

