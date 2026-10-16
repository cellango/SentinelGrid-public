# SentinelGridIAM Database

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-11-28  
**Status:** Database Design Complete

---

## Overview

**Database Name:** `SentinelGridIAM`

**Purpose:** Dedicated database for all Identity and Access Management (IAM) features

**Features:**
- ✅ Entitlements management
- ✅ Access certifications
- ✅ Audit campaigns
- ✅ Governance workflows
- ✅ Future IAM features (user lifecycle, access requests, etc.)

---

## Why Separate Database?

### Benefits

1. **Isolation**
   - Clean separation from application data
   - Independent schema evolution
   - No impact on application database migrations

2. **Security**
   - Separate access controls
   - Easier compliance auditing
   - Isolated backup/restore

3. **Scalability**
   - Independent scaling considerations
   - Separate connection pools
   - Can move to different instance if needed

4. **Maintenance**
   - Independent backup schedules
   - Separate monitoring
   - Clear ownership

---

## Database Structure

### Core Tables

#### Entitlements
- `entitlements` - Fine-grained permissions
- `role_entitlement_patterns` - Role-to-entitlement mapping

#### Governance
- `audit_campaigns` - Access review campaigns
- `certifications` - Entitlement certifications
- `audit_schedules` - Scheduled audit configuration

#### Audit
- `entitlement_audit_log` - Complete audit trail
- `certification_history` - Certification change history

#### References
- `tenant_references` - Tenant validation cache (synced from `sg.tenants`)

---

## Cross-Database Considerations

### Tenant References

**Challenge:** `tenant_id` in IAM database references `tenants.id` in `sg` database

**Solution:**
1. **No Foreign Keys** - Removed FK constraints (cross-database not supported)
2. **Application Validation** - Entitlement Agent validates `tenant_id` exists
3. **Reference Table** - `tenant_references` table for local validation (optional)
4. **Sync Job** - Periodic sync from `sg.tenants` to `tenant_references`

### Tenant Validation

**Application-Level:**
```python
# In Entitlement Agent
async def validate_tenant(tenant_id: UUID) -> bool:
    # Query sg database via API or direct connection
    async with get_db_connection('sg') as conn:
        result = await conn.execute(
            "SELECT id FROM tenants WHERE id = $1 AND status = 'active'",
            tenant_id
        )
        return result.rowcount > 0
```

**Database-Level (Optional):**
```sql
-- Use tenant_references table (synced from sg)
SELECT validate_tenant_id('6306bd5e-0bf2-4622-b789-ba0d18ae8003');
```

---

## Initialization

### Automatic (Docker Compose)

The database is automatically created on first PostgreSQL startup via:
- `init-iam-db.sh` script in `/docker-entrypoint-initdb.d/`

### Manual

```bash
# Create database
docker-compose exec postgres psql -U sg -d postgres << EOF
CREATE DATABASE "SentinelGridIAM";
GRANT ALL PRIVILEGES ON DATABASE "SentinelGridIAM" TO sg;
EOF

# Run migrations
docker-compose up entitlement_agent_flyway
```

---

## Migration Management

### Flyway Container

**Service:** `entitlement_agent_flyway`

**Configuration:**
- Database: `SentinelGridIAM`
- Version Table: `schema_version_iam`
- Migrations: `backend/services/entitlement_agent/migrations/`

### Running Migrations

```bash
# Run all pending migrations
docker-compose up entitlement_agent_flyway

# Check migration status
docker-compose run entitlement_agent_flyway info

# Validate migrations
docker-compose run entitlement_agent_flyway validate
```

---

## Connection Strings

### For Applications

**Python (SQLAlchemy):**
```python
DB_URL = "postgresql://sg:sg@postgres:5432/SentinelGridIAM"
```

**Environment Variable:**
```bash
IAM_DB_URL=postgresql://sg:sg@postgres:5432/SentinelGridIAM
```

### For Flyway

**Configuration:**
```conf
flyway.url=jdbc:postgresql://postgres:5432/SentinelGridIAM
flyway.user=sg
flyway.password=sg
```

---

## Tenant Reference Sync

### Manual Sync Script

```sql
-- From application or scheduled job
-- Sync tenant_references from sg.tenants

INSERT INTO tenant_references (id, name, slug, status, created_at, updated_at)
SELECT id, name, slug, status, created_at, updated_at
FROM dblink('host=postgres dbname=sg user=sg password=sg',
  'SELECT id, name, slug, status, created_at, updated_at FROM tenants')
AS t(id UUID, name TEXT, slug TEXT, status TEXT, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name,
    slug = EXCLUDED.slug,
    status = EXCLUDED.status,
    updated_at = EXCLUDED.updated_at,
    last_synced_at = NOW();
```

### Application-Level Sync

```python
# Periodic job in Entitlement Agent
async def sync_tenant_references():
    async with get_db_connection('sg') as sg_conn:
        async with get_db_connection('SentinelGridIAM') as iam_conn:
            tenants = await sg_conn.fetch("SELECT * FROM tenants")
            for tenant in tenants:
                await iam_conn.execute("""
                    INSERT INTO tenant_references 
                    (id, name, slug, status, created_at, updated_at, last_synced_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    ON CONFLICT (id) DO UPDATE
                    SET name = EXCLUDED.name,
                        slug = EXCLUDED.slug,
                        status = EXCLUDED.status,
                        updated_at = EXCLUDED.updated_at,
                        last_synced_at = NOW()
                """, tenant['id'], tenant['name'], tenant['slug'], 
                    tenant['status'], tenant['created_at'], tenant['updated_at'])
```

---

## Backup & Restore

### Backup

```bash
# Backup IAM database
docker-compose exec postgres pg_dump -U sg SentinelGridIAM > backup-iam-$(date +%Y%m%d).sql

# Or using volume backup
docker-compose exec postgres pg_dump -U sg SentinelGridIAM | gzip > backup-iam-$(date +%Y%m%d).sql.gz
```

### Restore

```bash
# Restore IAM database
docker-compose exec -T postgres psql -U sg SentinelGridIAM < backup-iam-20251128.sql

# Or from compressed
gunzip < backup-iam-20251128.sql.gz | docker-compose exec -T postgres psql -U sg SentinelGridIAM
```

---

## Monitoring

### Database Size

```sql
SELECT pg_size_pretty(pg_database_size('SentinelGridIAM'));
```

### Table Sizes

```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Migration Status

```sql
SELECT * FROM schema_version_iam ORDER BY installed_rank;
```

---

## Future IAM Features

This database will support additional IAM features:

- **Access Requests:** Users requesting additional entitlements
- **User Lifecycle:** Onboarding/offboarding workflows
- **Approval Workflows:** Multi-level approval chains
- **Integration Audits:** Third-party access reviews
- **Compliance Reports:** Automated compliance reporting
- **Risk Scoring:** Entitlement risk analysis

---

## Related Documentation

- `ENTITLEMENTS_DATABASE_SCHEMA.md` - Complete schema documentation
- `ENTITLEMENTS_DESIGN.md` - Design overview
- `ENTITLEMENTS_IMPLEMENTATION_PLAN.md` - Implementation plan

