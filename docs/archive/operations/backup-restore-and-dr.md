# Backup, Restore, And Disaster Recovery

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Purpose

Define the backup cadence, restore path, and drill expectations for the launch-scope production stack.

## Protected Components

- PostgreSQL
- Keycloak realm and IAM configuration export

## Canonical Scripts

- `infra/shared/scripts/backup-postgres.sh`
- `infra/shared/scripts/backup-keycloak.sh`
- `infra/shared/scripts/restore-system.sh`
- `infra/shared/scripts/run-restore-drill.sh`
- `infra/shared/scripts/run-release-rollback-drill.sh`

## Backup Cadence

- PostgreSQL: daily scheduled backup plus pre-release ad hoc backup
- Keycloak export: daily scheduled backup plus pre-release ad hoc backup
- Restore drill: at least monthly in staging

## Recommended Recovery Objectives

- RPO: 24 hours maximum
- RTO: 4 hours target for launch scope

## Slice 6B Drill Timeboxes

- PostgreSQL restore drill: 20 minutes
- Keycloak restore drill: 30 minutes
- Combined `all` restore drill: 45 minutes

Every restore drill must save:

- `result.json`
- `summary.md`
- `operator-actions.md`

and the result must include measured duration plus whether the run stayed inside the declared timebox.

## PostgreSQL Backup

Example:

```bash
POSTGRES_HOST=<host> \
POSTGRES_PORT=5432 \
POSTGRES_USER=<user> \
POSTGRES_PASSWORD=<password> \
POSTGRES_DB=sg \
BACKUP_DIR=/var/backups/sentinelgrid/postgres \
S3_BACKUP_BUCKET=<bucket> \
./infra/shared/scripts/backup-postgres.sh
```

Client-version note:

- prefer PostgreSQL client tools that match the target server major version
- the restore path now strips the known `SET transaction_timeout = 0;` header emitted by newer host `pg_dump` versions when restoring into PostgreSQL 16, while still using `ON_ERROR_STOP=1` to fail closed on real SQL errors

## Keycloak Backup

Preferred auth mode is service-account based:

```bash
KEYCLOAK_URL=https://identity.example.com \
KEYCLOAK_ADMIN_REALM=master \
KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT=true \
KEYCLOAK_ADMIN_CLIENT_ID=sentinelgrid-ops-backup \
KEYCLOAK_ADMIN_CLIENT_SECRET=<secret> \
S3_BACKUP_BUCKET=<bucket> \
./infra/shared/scripts/backup-keycloak.sh
```

Break-glass username/password mode is still supported, but should only be used with short-lived credentials.

## Full Restore

Restore the latest or a named backup:

```bash
./infra/shared/scripts/restore-system.sh postgres
./infra/shared/scripts/restore-system.sh keycloak
./infra/shared/scripts/restore-system.sh all
```

For drill evidence, prefer the wrapper:

```bash
./infra/shared/scripts/run-restore-drill.sh --component all --mode live
```

Examples with explicit timeboxes:

```bash
./infra/shared/scripts/run-restore-drill.sh --component postgres --mode live --timebox-minutes 20
./infra/shared/scripts/run-restore-drill.sh --component keycloak --mode live --timebox-minutes 30
```

## Restore Drill Procedure

1. Pick the backup set and record the target timestamp.
2. Restore into a non-production environment.
3. Bring up IAM, API gateway, SIEM, orchestrator, model gateway, and frontend.
4. Verify login, dashboard, alerts, incidents, and onboarding.
5. Record actual restore time and any manual fixes required.

The drill wrapper stores evidence under:

```text
artifacts/drills/restore/<YYYY-MM-DD>/<run-id>/
```

Use `--mode plan` when preparing the drill without executing restore:

```bash
./infra/shared/scripts/run-restore-drill.sh --component postgres --mode plan
```

The wrapper now generates an `operator-actions.md` checklist so the expected recovery sequence is frozen with the drill artifact instead of left to memory.

## Security Requirements

- Store backups encrypted at rest.
- Restrict backup bucket and restore access to the platform/SRE security group.
- Prefer service-account auth for Keycloak export and restore tooling.
- Rotate any break-glass credentials used during restore drills.

## Failure Escalation

Escalate immediately if:

- a scheduled backup is missing
- restore verification fails
- backup archives cannot be decrypted
- Keycloak export is incomplete or corrupted

## Evidence To Save

- backup file names and timestamps
- storage location
- restore drill notes
- measured RPO/RTO
- timebox compliance from `result.json`
- `operator-actions.md`
- wrapper evidence directory when `run-restore-drill.sh` is used
