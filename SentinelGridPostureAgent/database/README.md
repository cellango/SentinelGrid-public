# Database Migrations

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This directory contains Alembic migrations for the posture platform database.

## Setup

1. Ensure PostgreSQL is running:
   ```bash
   docker-compose up -d posture-postgres
   ```

2. Initialize Alembic (already done):
   ```bash
   cd database
   alembic init alembic
   ```

## Creating Migrations

### Auto-generate from model changes:
```bash
cd database
alembic revision --autogenerate -m "description of changes"
```

### Manual migration:
```bash
cd database
alembic revision -m "description of changes"
# Edit the generated file in alembic/versions/
```

## Running Migrations

### Upgrade to latest:
```bash
cd database
alembic upgrade head
```

### Upgrade to specific revision:
```bash
alembic upgrade <revision_id>
```

### Downgrade one revision:
```bash
alembic downgrade -1
```

### Show current revision:
```bash
alembic current
```

### Show migration history:
```bash
alembic history
```

## Database Schema

The database includes the following tables:

- **observables**: Entities that can be analyzed (assets, repos, images)
- **assets**: Physical/logical assets in infrastructure
- **findings**: Unified security findings from all analyzers
- **analyzer_jobs**: Track analyzer execution jobs
- **posture_scores**: Calculated posture metrics
- **cloud_accounts**: Connected cloud accounts for scanning
- **repositories**: Code repositories for scanning

## Environment Variables

Set these before running migrations:

```bash
export DATABASE_URL="postgresql://posture_user:posture_pass@localhost:5433/posture_db"
```

Or use the default from alembic.ini.

