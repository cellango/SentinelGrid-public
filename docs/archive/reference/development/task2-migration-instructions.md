# Task 2: Database Migration - Instructions

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Issue: pgvector Extension Not Available

The PostgreSQL container needs the `pgvector` extension installed.

## Solution: Use pgvector-Enabled PostgreSQL Image

**Updated:** `docker-compose.dev.yml` now uses `pgvector/pgvector:pg16` instead of `postgres:16-alpine`

## Steps to Run Migration

### Option 1: Restart PostgreSQL with pgvector Image (RECOMMENDED)

```bash
# Stop current postgres container
docker-compose -f docker-compose.dev.yml stop postgres

# Remove container (data will persist in volume)
docker-compose -f docker-compose.dev.yml rm -f postgres

# Start with new image
docker-compose -f docker-compose.dev.yml up -d postgres

# Wait for PostgreSQL to be ready
docker-compose -f docker-compose.dev.yml exec postgres pg_isready -U sg

# Run migration
cat backend/services/model_gateway/db/migrations/V1__create_llm_training_schema.sql | \
  docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg
```

### Option 2: Manual pgvector Installation (Alternative)

If you prefer to keep the current PostgreSQL image:

```bash
# Install build dependencies
docker-compose -f docker-compose.dev.yml exec postgres sh -c \
  "apk add --no-cache build-base git postgresql16-dev"

# Build and install pgvector from source
docker-compose -f docker-compose.dev.yml exec postgres sh -c \
  "cd /tmp && git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git && \
   cd pgvector && make && make install"

# Restart PostgreSQL
docker-compose -f docker-compose.dev.yml restart postgres

# Run migration
cat backend/services/model_gateway/db/migrations/V1__create_llm_training_schema.sql | \
  docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg
```

## Verify Migration

```bash
# Check extensions
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -c \
  "SELECT extname, extversion FROM pg_extension WHERE extname IN ('uuid-ossp', 'vector');"

# Check tables
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -c \
  "\dt" | grep -E "(tenant_training_data|tenant_model_adapters|cybersecurity_knowledge_base)"

# Check RLS policies
docker-compose -f docker-compose.dev.yml exec -T postgres psql -U sg -d sg -c \
  "SELECT schemaname, tablename, policyname FROM pg_policies WHERE schemaname = 'public';"
```

## Expected Output

After successful migration, you should see:

1. **Extensions:**
   - `uuid-ossp`
   - `vector`

2. **Tables:**
   - `tenant_training_data`
   - `tenant_model_adapters`
   - `adapter_version_history`
   - `adapter_training_jobs`
   - `training_data_snapshots`
   - `cybersecurity_knowledge_base`

3. **RLS Policies:**
   - One policy per table for tenant isolation

## Troubleshooting

### Error: "extension vector is not available"

**Cause:** pgvector not installed in PostgreSQL container

**Solution:** Use Option 1 (recommended) to switch to `pgvector/pgvector:pg16` image

### Error: "relation does not exist"

**Cause:** Migration failed partway through

**Solution:** 
1. Drop existing tables if partial migration occurred
2. Re-run full migration

### Error: "there is no unique constraint matching given keys"

**Cause:** Foreign key reference issue in migration

**Solution:** Check migration file order - tables must be created before foreign keys

