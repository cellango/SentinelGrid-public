# Entitlements Database Schema Design

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-11-28  
**Status:** Schema Design Complete  
**Migration Tool:** Flyway (Separate Container)

---

## Executive Summary

Keycloak does **NOT** provide built-in database models for entitlement management or governance features. We need a **separate database schema** managed by **Flyway in a dedicated container** to support:

- Fine-grained entitlements
- Audit campaigns and certifications
- Governance workflows
- Complete audit trail

---

## Keycloak Limitations

### What Keycloak Provides:
- ✅ User management
- ✅ Role management (RBAC)
- ✅ Authorization Services (for resource-level permissions)
- ✅ Basic audit logs

### What Keycloak Does NOT Provide:
- ❌ Entitlement lifecycle management
- ❌ Access certification workflows
- ❌ Scheduled audit campaigns
- ❌ Governance features (annual/monthly reviews)
- ❌ User attestation workflows
- ❌ Auto-revocation based on certifications
- ❌ Custom entitlement audit trail

**Conclusion:** We need our own schema for entitlement governance.

---

## Schema Architecture

### Schema Location
- **Schema:** `public` (shared with other services)
- **Namespace:** Tables prefixed to avoid conflicts
- **Management:** Flyway in separate container

### Key Design Decisions

1. **Separate Flyway Container**
   - Isolated schema management
   - Independent deployment
   - Version-controlled migrations

2. **Shared Database, Separate Schema Management**
   - Uses existing PostgreSQL instance
   - Separate `schema_version` table (`schema_version_entitlements`)
   - Coexists with other service schemas

3. **Tenant Isolation**
   - All tables include `tenant_id`
   - Foreign keys to `tenants` table
   - Indexes optimized for tenant-scoped queries

---

## Table Structure

### Core Tables

#### 1. `entitlements`
Primary table storing all entitlements.

**Key Fields:**
- `tenant_id` - Multi-tenant isolation
- `resource_type`, `resource_id`, `action` - Entitlement pattern
- `granted_to_type`, `granted_to_id` - User/role/group
- `status` - active/expired/revoked/pending_review
- `expires_at` - Optional expiration
- `usage_count_90d`, `last_used_at` - Usage tracking

**Pattern:** `{resource_type}:{resource_id}:{action}@{tenant_id}`

#### 2. `audit_campaigns`
Audit campaigns for access reviews.

**Key Fields:**
- `campaign_type` - scheduled/on_demand/continuous/event_triggered
- `status` - draft/scheduled/active/in_review/completed
- `scope` - JSONB filters for entitlements/users
- `review_config` - Reviewer assignment rules
- `schedule` - Start/end dates, reminders

#### 3. `certifications`
Individual entitlement certifications within campaigns.

**Key Fields:**
- `certifier_type` - self/manager/admin/delegated
- `status` - pending/approved/revoked/questioned/deferred
- `decision` - approve/revoke/question/defer/modify
- `justification` - Reviewer's reason
- `deadline` - Review deadline

#### 4. `audit_schedules`
Configuration for scheduled audits.

**Key Fields:**
- `entitlement_pattern` - Pattern to match entitlements
- `frequency` - monthly/quarterly/annual/continuous
- `reviewer_type` - self/manager/admin
- `auto_revoke_days` - Days after deadline to auto-revoke

### Audit Tables

#### 5. `entitlement_audit_log`
Complete audit trail of entitlement changes.

#### 6. `certification_history`
History of certification status changes.

### Mapping Tables

#### 7. `role_entitlement_patterns`
Maps Keycloak roles to entitlement patterns.

**Purpose:** Auto-create entitlements when roles are assigned.

---

## Flyway Configuration

### Container Setup

```yaml
entitlement_agent_flyway:
  build:
    context: ./backend/services/entitlement_agent
    dockerfile: Dockerfile.flyway
  environment:
    - DB_HOST=postgres
    - DB_PORT=5432
    - DB_NAME=sg
    - DB_USER=sg
    - DB_PASSWORD=${DB_PASSWORD:-sg}
  volumes:
    - ./backend/services/entitlement_agent/migrations:/flyway/sql
  depends_on:
    postgres:
      condition: service_healthy
  command: migrate
```

### Migration Files

**Location:** `backend/services/entitlement_agent/migrations/`

**Naming:** `V{version}__{description}.sql`

**Example:**
- `V1__create_entitlements_schema.sql`
- `V2__add_indexes_for_performance.sql`
- `V3__add_role_mapping_tables.sql`

### Schema Version Table

**Table:** `schema_version_entitlements`

**Purpose:** Flyway tracks applied migrations here.

---

## Integration with Existing Schema

### Dependencies

**References:**
- `tenants` table (from `001_initial_schema.sql`)
- Foreign key: `entitlements.tenant_id → tenants.id`

**No Circular Dependencies:**
- Entitlement schema is independent
- Can be deployed after initial schema
- Optional feature (can be disabled)

### Coexistence

**Shared Database:**
- Same PostgreSQL instance
- Same `public` schema
- Different version tables

**Isolation:**
- Separate Flyway container
- Separate migration history
- No conflicts with other services

---

## Migration Strategy

### Initial Deployment

1. **Deploy Base Schema** (existing)
   ```bash
   # Already exists: 001_initial_schema.sql
   ```

2. **Deploy Entitlement Schema**
   ```bash
   docker-compose up entitlement_agent_flyway
   ```

3. **Verify**
   ```sql
   SELECT * FROM schema_version_entitlements;
   SELECT COUNT(*) FROM entitlements;
   ```

### Future Migrations

1. **Add New Migration File**
   ```
   V2__add_feature.sql
   ```

2. **Flyway Auto-Detects**
   - Compares `schema_version_entitlements`
   - Applies new migrations
   - Updates version table

---

## Benefits of Separate Flyway Container

### ✅ Advantages

1. **Isolated Deployment**
   - Deploy schema changes independently
   - No impact on application containers
   - Rollback without app restart

2. **Version Control**
   - All migrations in git
   - Clear migration history
   - Reproducible across environments

3. **CI/CD Integration**
   - Run migrations in pipeline
   - Test schema changes separately
   - Validate before app deployment

4. **Multi-Environment**
   - Same migrations for dev/staging/prod
   - Environment-specific configs
   - Consistent schema across environments

5. **Team Collaboration**
   - Clear migration ownership
   - Conflict-free schema changes
   - Reviewable migration scripts

---

## Schema Size Estimates

### Table Sizes (Estimated)

| Table | Rows (1k tenants) | Size |
|-------|------------------|------|
| `entitlements` | ~500k | ~500 MB |
| `audit_campaigns` | ~4k (4/year/tenant) | ~10 MB |
| `certifications` | ~2M (500 ent/campaign) | ~2 GB |
| `entitlement_audit_log` | ~5M | ~5 GB |
| `audit_schedules` | ~10k | ~5 MB |

**Total:** ~7.5 GB for 1,000 tenants

### Indexes
- Additional ~30% overhead
- Optimized for tenant-scoped queries

---

## Performance Considerations

### Indexes

**Critical Indexes:**
- `idx_entitlements_tenant` - Tenant isolation
- `idx_entitlements_granted_to` - User lookup
- `idx_entitlements_pattern` - Pattern matching
- `idx_certifications_deadline` - Pending reviews

### Query Patterns

**Most Common:**
1. Get user entitlements (by tenant)
2. Evaluate access (pattern matching)
3. List pending certifications
4. Campaign statistics

**All Optimized with Indexes**

---

## Security

### Access Control

- **Application:** Full CRUD via Entitlement Agent
- **Flyway:** Read-only migrations, no data access
- **Database:** Role-based access (separate user for Flyway)

### Data Protection

- **Encryption:** At rest (PostgreSQL)
- **Audit:** All changes logged
- **Backup:** Included in database backups

---

## Maintenance

### Regular Tasks

1. **Expire Old Entitlements**
   ```sql
   SELECT expire_entitlements();
   ```

2. **Archive Old Audit Logs**
   - Archive after retention period
   - Move to cold storage

3. **Cleanup Expired Campaigns**
   - Archive completed campaigns
   - Remove old certification data

---

## Rollback Strategy

### Migration Rollback

**Flyway Limitations:**
- No automatic rollback
- Manual rollback scripts required

**Approach:**
- Create rollback scripts: `R{version}__{description}.sql`
- Test rollbacks in staging
- Document rollback procedures

**Example:**
```sql
-- R1__drop_entitlements_schema.sql
DROP TABLE IF EXISTS entitlements CASCADE;
DROP TABLE IF EXISTS audit_campaigns CASCADE;
-- etc.
```

---

## Monitoring

### Metrics to Track

1. **Schema Health**
   - Migration status
   - Last migration date
   - Migration failures

2. **Data Health**
   - Entitlement counts
   - Expired entitlements
   - Pending certifications

3. **Performance**
   - Query latency
   - Index usage
   - Table sizes

---

## Next Steps

1. ✅ Schema design complete
2. ⏳ Create Flyway container configuration
3. ⏳ Add to docker-compose.dev.yml
4. ⏳ Test migration in dev environment
5. ⏳ Create rollback procedures

---

**Related Documents:**
- `ENTITLEMENTS_DESIGN.md` - Complete design
- `ENTITLEMENTS_GOVERNANCE.md` - Governance features
- `ENTITLEMENTS_IMPLEMENTATION_PLAN.md` - Implementation plan

