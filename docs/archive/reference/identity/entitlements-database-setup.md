# SentinelGridIAM Database Setup Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Quick Reference for Database Setup**

---

## Database Overview

**Name:** `SentinelGridIAM`  
**Purpose:** All IAM-related features (entitlements, governance, audits, future IAM features)  
**Instance:** Same PostgreSQL server as `sg` database  

---

## Automatic Setup

### Method 1: Postgres Init Script (First Startup Only)
If starting a fresh postgres container, the database is created automatically via:
- `init-iam-db.sh` in `/docker-entrypoint-initdb.d/`
- Only runs when data directory is empty

### Method 2: Flyway Container (Recommended)
The Flyway container automatically creates the database if it doesn't exist:
- Built into `Dockerfile.flyway`
- Runs `ensure-db-exists.sh` before migrations
- Works for existing postgres instances

```bash
# This will create database if missing, then run migrations
docker-compose up entitlement_agent_flyway
```

---

## Manual Setup

### Create Database Manually

```bash
# Option 1: Use helper script
./backend/services/entitlement_agent/scripts/create-iam-db.sh

# Option 2: Direct SQL
docker-compose exec postgres psql -U sg -d postgres << EOF
CREATE DATABASE "SentinelGridIAM";
GRANT ALL PRIVILEGES ON DATABASE "SentinelGridIAM" TO sg;
EOF
```

### Verify Database Exists

```bash
docker-compose exec postgres psql -U sg -d postgres -c '\l' | grep SentinelGridIAM
```

---

## Running Migrations

```bash
# Run all pending migrations
docker-compose up entitlement_agent_flyway

# Check migration status
docker-compose run entitlement_agent_flyway info

# Validate migrations (without applying)
docker-compose run entitlement_agent_flyway validate
```

---

## Verify Setup

```sql
-- Connect to database
docker-compose exec postgres psql -U sg -d SentinelGridIAM

-- Check tables
\dt

-- Check migration status
SELECT * FROM schema_version_iam ORDER BY installed_rank;

-- Verify entitlements table
SELECT COUNT(*) FROM entitlements;
```

---

## Troubleshooting

### Database doesn't exist error
```bash
# Create manually
./backend/services/entitlement_agent/scripts/create-iam-db.sh
```

### Migration fails
```bash
# Check logs
docker-compose logs entitlement_agent_flyway

# Verify database exists
docker-compose exec postgres psql -U sg -d postgres -c "SELECT datname FROM pg_database WHERE datname='SentinelGridIAM';"
```

### Reset database (CAUTION)
```bash
# Drop and recreate
docker-compose exec postgres psql -U sg -d postgres -c 'DROP DATABASE IF EXISTS "SentinelGridIAM";'
docker-compose exec postgres psql -U sg -d postgres -c 'CREATE DATABASE "SentinelGridIAM";'
docker-compose up entitlement_agent_flyway
```

---

**Related:**
- `SENTINELGRIDIAM_DATABASE.md` - Complete database documentation
- `ENTITLEMENTS_DATABASE_SCHEMA.md` - Schema details

