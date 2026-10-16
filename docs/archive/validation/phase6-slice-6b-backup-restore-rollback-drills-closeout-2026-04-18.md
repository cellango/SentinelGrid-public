# Phase 6 Slice 6B Closeout: Backup, Restore, And Rollback Drills

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** April 18, 2026  
**Scope:** Narrowed launch-scope recovery drills for PostgreSQL, Keycloak, and Helm rollback  
**Decision:** Closed for the narrowed launch scope  
**Gate impact:** Advances `G-10` with fresh local live recovery evidence; `G-10` remains open until support rehearsal and final dry-run slices are closed

## Goal

Prove that the narrowed launch package can be recovered and rolled back recently enough to trust:

1. rerun restore drills for all stateful launch dependencies
2. rerun a Helm rollback drill for a launch-like deployment
3. record timeboxes and explicit operator actions with the evidence

## Repo-Backed Changes

### Restore and rollback drill wrappers now record real recovery metadata

The live drill wrappers now capture:

- `started_at_utc`
- `ended_at_utc`
- `duration_seconds`
- `timebox_minutes`
- `within_timebox`
- `operator-actions.md`

That work landed in:

- `infra/shared/scripts/run-restore-drill.sh`
- `infra/shared/scripts/run-release-rollback-drill.sh`

This closes a real evidence gap from the earlier wrappers, which only captured command intent and pass/fail state.

### Backup and restore scripts now fail closed instead of reporting false success

The live PostgreSQL backup rehearsal exposed a real defect: `backup-postgres.sh` could report success after a failed `pg_dump` because the pipeline did not use `pipefail`. The PostgreSQL restore path also allowed SQL errors to pass silently because `psql` was not running with `ON_ERROR_STOP`.

Those defects are now fixed in:

- `infra/shared/scripts/backup-postgres.sh`
- `infra/shared/scripts/backup-keycloak.sh`
- `infra/shared/scripts/restore-system.sh`

The important hardening changes are:

- `set -euo pipefail` on backup and restore scripts
- gzip archive validation for PostgreSQL backups
- fail-closed `curl -fsS` usage for Keycloak backup and restore auth paths
- explicit defaults for optional env vars under `set -u`
- `psql -v ON_ERROR_STOP=1` for restore execution
- stripping the known `SET transaction_timeout = 0;` header mismatch emitted by host `pg_dump 17.x` when restoring into PostgreSQL 16

This slice therefore did not just produce new drill evidence. It also fixed two recovery-script bugs that would have made that evidence untrustworthy.

### The recovery runbooks now carry explicit timeboxes and artifact expectations

The narrowed launch recovery contract is now documented in:

- `docs/archive/operations/backup-restore-and-dr.md`
- `docs/archive/operations/production-release-and-deploy.md`

The runbooks now define:

- restore drill timeboxes for PostgreSQL, Keycloak, and `all`
- rollback drill timebox for the narrowed launch path
- required artifact files
- the operator-action checklist artifact produced by the wrappers
- the PostgreSQL client-version note for host-tooling versus server-version skew

## Fresh Live Evidence

### PostgreSQL backup and restore

- Backup:
  - `artifacts/drills/backups/phase6-2026-04-18/postgres-live/sentinelgrid_db_20260418_115115.sql.gz`
- Restore drill:
  - `artifacts/drills/restore/2026-04-18/165655-postgres-live/`

Result:

- status: `passed`
- duration: `3s`
- timebox: `20m`
- within timebox: `true`

The restore log shows the database was restored and the table verification completed with `125` public-schema tables present.

### Keycloak backup and restore

- Backup:
  - `artifacts/drills/backups/phase6-2026-04-18/keycloak-live/keycloak_20260418_115845.tar.gz`
- Restore drill:
  - `artifacts/drills/restore/2026-04-18/165858-keycloak-live/`

Result:

- status: `passed`
- duration: `0s`
- timebox: `30m`
- within timebox: `true`

The restore log shows successful authentication and restore of both `demo` and `master` realms.

### Helm rollback drill

- Rollback drill:
  - `artifacts/drills/rollback/2026-04-18/170133-phase6-rollback-smoke-rollback-live/`

Supporting history check:

- `helm history phase6-rollback-smoke -n sg-core`

Result:

- status: `passed`
- duration: `3s`
- timebox: `15m`
- within timebox: `true`

The Helm history shows:

- revision `1`: install
- revision `2`: upgrade
- revision `3`: rollback to `1`

## Verification

### Script and wrapper validation

- `bash -n infra/shared/scripts/backup-postgres.sh infra/shared/scripts/backup-keycloak.sh infra/shared/scripts/restore-system.sh infra/shared/scripts/run-restore-drill.sh infra/shared/scripts/run-release-rollback-drill.sh`
- result: passed

### Local live recovery path executed on April 18, 2026

1. `docker compose -f docker-compose.minimal.yml up -d postgres`
2. `BACKUP_DIR=... POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_USER=sg POSTGRES_PASSWORD=sg POSTGRES_DB=sg bash infra/shared/scripts/backup-postgres.sh`
3. `BACKUP_DIR=... POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_USER=sg POSTGRES_PASSWORD=sg POSTGRES_DB=sg bash infra/shared/scripts/run-restore-drill.sh --component postgres --backup-file ... --mode live --timebox-minutes 20`
4. `docker compose -f docker-compose.minimal.yml up -d keycloak_db keycloak`
5. `BACKUP_DIR=... KEYCLOAK_URL=http://localhost:8080 KEYCLOAK_ADMIN_REALM=master KEYCLOAK_ADMIN_USER=admin KEYCLOAK_ADMIN_PASSWORD=admin KEYCLOAK_ADMIN_CLIENT_ID=admin-cli bash infra/shared/scripts/backup-keycloak.sh`
6. `BACKUP_DIR=... KEYCLOAK_URL=http://localhost:8080 KEYCLOAK_ADMIN_REALM=master KEYCLOAK_ADMIN_USER=admin KEYCLOAK_ADMIN_PASSWORD=admin KEYCLOAK_ADMIN_CLIENT_ID=admin-cli bash infra/shared/scripts/run-restore-drill.sh --component keycloak --backup-file ... --mode live --timebox-minutes 30`
7. `kind create cluster --name phase6-slice6b-20260418`
8. `helm install phase6-rollback-smoke charts/common-service -n sg-core --create-namespace -f charts/values/phase6-rollback-smoke.yaml --set podAnnotations.drillRevision=rev1 --wait --timeout 180s`
9. `helm upgrade phase6-rollback-smoke charts/common-service -n sg-core -f charts/values/phase6-rollback-smoke.yaml --set podAnnotations.drillRevision=rev2 --wait --timeout 180s`
10. `bash infra/shared/scripts/run-release-rollback-drill.sh --release phase6-rollback-smoke --revision 1 --namespace sg-core --mode live --timebox-minutes 15`
11. `helm history phase6-rollback-smoke -n sg-core`

## Residuals

- This slice proves the local live recovery path, not a stage or production-cluster recovery path. A deploy-target rerun is still recommended before the final `Go` re-audit.
- The local Keycloak drill used break-glass admin credentials against the compose environment because that local drill stack does not provision a dedicated service-account backup client. That is acceptable for local rehearsal, not as a production operating model.
- The disposable kind cluster `phase6-slice6b-20260418` remains created after the drill. It can be removed later with `kind delete cluster --name phase6-slice6b-20260418`.
- `G-10` remains open until `Slice 6C` and `Slice 6D` are also complete.

## Decision

For the narrowed launch scope:

- Phase 6 Slice 6B is closed
- fresh live backup, restore, and rollback evidence now exists for April 18, 2026
- the recovery tooling is stricter and more trustworthy than it was before this slice
- Phase 6 should continue with `Slice 6C`
