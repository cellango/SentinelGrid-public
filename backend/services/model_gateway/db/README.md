# Model Gateway Database Migrations

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../../RELEASE_SCOPE.md) first.


This directory contains Flyway migrations for the Model Gateway service.

## Migration Types

### Schema Migrations (SQL)
- **Location:** `migrations/*.sql`
- **Tool:** Flyway
- **Format:** `V<version>__<description>.sql`
- **Purpose:** Database schema changes (tables, indexes, constraints)

### Data Migrations (Python)
- **Location:** `scripts/load_knowledge_base_data.py`
- **Tool:** Python script
- **Tracking:** `data_migration_history` table
- **Purpose:** Load data with complex processing (e.g., generating embeddings)

## Architecture

```
┌─────────────────┐
│  Flyway (SQL)   │  → Schema migrations
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Data Migrator  │  → Python scripts for data loading
│     (Python)    │     - Checks migration markers
└─────────────────┘     - Loads data with embeddings
                         - Updates migration status
```

## Running Migrations

### Automatic (Docker Compose)

Migrations run automatically when starting services:

```bash
# Schema migrations (Flyway)
docker-compose -f docker-compose.dev.yml up model_gateway_migrations

# Data migrations (Python)
docker-compose -f docker-compose.dev.yml up model_gateway_data_migrations
```

### Manual Execution

#### Schema Migrations (Flyway)

```bash
cd backend/services/model_gateway/db
docker build -t model-gateway-flyway -f Dockerfile.flyway .
docker run --rm \
  -e FLYWAY_URL=jdbc:postgresql://localhost:5432/sg \
  -e FLYWAY_USER=sg \
  - FLYWAY_PASSWORD=sg \
  --network host \
  model-gateway-flyway
```

#### Data Migrations (Python)

```bash
cd backend/services/model_gateway

# Install dependencies
pip install -r requirements-loader.txt

# Run data migrations
python db/scripts/load_knowledge_base_data.py
```

## Migration Files

### Schema Migrations

- **V1.0** - `create_llm_training_schema.sql`
  - Creates tables for training data, adapters, jobs
  - Creates `cybersecurity_knowledge_base` table
  - Sets up pgvector extension

- **V1.1** - `mark_knowledge_base_data_load.sql`
  - Creates `data_migration_history` table
  - Inserts marker for knowledge base data load

### Data Migrations

- **V1.1** - `load_knowledge_base_data.py`
  - Loads NIST, MITRE, OWASP, Playbooks
  - Generates embeddings
  - Updates migration status

## Data Migration Tracking

The `data_migration_history` table tracks Python-based data migrations:

```sql
SELECT migration_version, migration_name, status, records_loaded, completed_at
FROM data_migration_history
ORDER BY created_at;
```

**Status Values:**
- `pending` - Migration hasn't run yet
- `running` - Migration is currently running
- `completed` - Migration completed successfully
- `failed` - Migration failed

## Creating New Migrations

### Schema Migration (SQL)

1. Create new file: `migrations/V1.2__your_description.sql`
2. Add SQL statements
3. Run Flyway migration

### Data Migration (Python)

1. **Add SQL marker** in schema migration:
   ```sql
   INSERT INTO data_migration_history (migration_version, migration_name, status)
   VALUES ('V1.2', 'Description of data load', 'pending');
   ```

2. **Create Python script** in `scripts/`:
   - Check migration status
   - Load data
   - Update migration status

3. **Update** `load_knowledge_base_data.py` or create new script

## Migration Status Check

```bash
# Check schema migrations (Flyway)
docker-compose -f docker-compose.dev.yml exec postgres psql -U sg -d sg -c "
SELECT version, description, installed_on, success 
FROM flyway_schema_history 
ORDER BY installed_rank;
"

# Check data migrations
docker-compose -f docker-compose.dev.yml exec postgres psql -U sg -d sg -c "
SELECT migration_version, migration_name, status, records_loaded, completed_at
FROM data_migration_history
ORDER BY created_at;
"
```

## Troubleshooting

### Schema Migration Failed

```bash
# Check Flyway logs
docker-compose -f docker-compose.dev.yml logs model_gateway_migrations

# Manual Flyway info
docker-compose -f docker-compose.dev.yml run --rm model_gateway_migrations info
```

### Data Migration Failed

```bash
# Check data migration logs
docker-compose -f docker-compose.dev.yml logs model_gateway_data_migrations

# Check migration status
docker-compose -f docker-compose.dev.yml exec postgres psql -U sg -d sg -c "
SELECT * FROM data_migration_history WHERE status = 'failed';
"

# Retry failed migration (reset status to pending)
docker-compose -f docker-compose.dev.yml exec postgres psql -U sg -d sg -c "
UPDATE data_migration_history SET status = 'pending' WHERE migration_version = 'V1.1';
"
```

### Reset Migration (Development Only)

⚠️ **WARNING:** Only use in development!

```bash
# Reset schema migrations
docker-compose -f docker-compose.dev.yml exec postgres psql -U sg -d sg -c "
DELETE FROM flyway_schema_history WHERE version >= '1.1';
"

# Reset data migrations
docker-compose -f docker-compose.dev.yml exec postgres psql -U sg -d sg -c "
DELETE FROM data_migration_history;
TRUNCATE cybersecurity_knowledge_base CASCADE;
"
```
