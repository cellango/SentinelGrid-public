# Database Migrations And Bootstrap

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Purpose

Run schema changes in a controlled way and keep seed/bootstrap usage separate from production migration execution.

## Core Scripts

- `scripts/lint_migrations_schema_only.sh`
- `scripts/flyway_schema_only.sh`
- `scripts/bootstrap_fresh_env.sh`

## Rules

- Production uses schema migration only. Do not run demo or bootstrap seed scripts in production.
- Any data backfill or one-off repair must be reviewed separately and recorded in the release notes.
- Take fresh backups before every production migration window.

## Preflight

1. Confirm the release branch is frozen.
2. Run migration lint:

```bash
./scripts/lint_migrations_schema_only.sh
```

3. Run the migration set in a staging environment that matches production engine versions.
4. Review impacted services and expected downtime, if any.

## Execute Schema Migrations

Example:

```bash
DB_HOST=<host> \
DB_PORT=5432 \
DB_NAME=sg \
DB_USER=<user> \
DB_PASSWORD=<password> \
./scripts/flyway_schema_only.sh
```

`flyway_schema_only.sh` will prefer:

- local Flyway
- Dockerized Flyway
- direct `psql`

## Fresh Environment Bootstrap

Use bootstrap only for new lower environments:

```bash
DB_HOST=localhost \
DB_PORT=5432 \
DB_NAME=sg \
DB_USER=sg \
DB_PASSWORD=sg \
./scripts/bootstrap_fresh_env.sh
```

This is for:

- local development
- integration environments
- clean-room audit rehearsal environments

It is not a production release step.

## Verification

After migration:

- check Flyway history
- verify required tables and columns exist
- run service `/ready` checks
- run focused smoke tests on login, onboarding, alerts, and incidents

## Rollback Guidance

- If the migration is backward-compatible and only the app is bad, roll back the service image first.
- If the schema itself is bad, stop traffic and execute the reviewed rollback or forward-fix plan.
- Do not improvise destructive SQL in production without a recorded approval and fresh backup.

## Evidence To Save

- migration command and operator
- database target and timestamp
- schema history diff
- verification output
- rollback decision if one was needed
