# Flyway Cleanup Plan (Baseline and Stray Migrations)

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


This doc summarizes how to stabilize migrations after adding the app catalog and privileged access tables.

## Current state
- Latest numbered migrations: `V066__add_app_catalog.sql`, `V067__add_privileged_access_table.sql`.
- Stray migrations normalized: `V068__add_anomalies_table.sql`, `V069__add_devices_table.sql` (previously `XXX_*`).
- Runtime creates some tables defensively (anomalies, privileged_access_requests); Flyway should own these going forward.
- Baseline smoke-test: `flyway migrate` against a fresh DB using only `backend/migrations/baseline` (contains `V100__baseline_full_schema.sql`) succeeded.

## Safe cleanup approach
1) **Snapshot**: Take a schema-only dump of the current DB after `V067` is applied (and app catalog seeded). Example:  
   `pg_dump --schema-only --no-owner --file=backups/schema_pre_baseline.sql "$DB_URL"`

2) **Baseline migration**: Generate `V100__baseline_full_schema.sql` from the snapshot so new environments start from the current schema in one shot. Include:
   - All tables up to V069 (users, assets/devices, anomalies, app_catalog, privileged_access_requests, birthright_rules, lifecycle schedule, etc.)
   - Indexes, FKs, defaults; keep `CREATE TABLE IF NOT EXISTS` where we rely on idempotency today.

3) **Archive legacy chain**: Keep `V001`–`V069` for history, but set Flyway config for fresh environments to `baselineVersion=100` + `baselineOnMigrate=true`. Optionally move older files into `migrations/archive/`.

4) **Repeatables**: Add `R__seed_app_catalog.sql` (and other reference data) so default content stays synced post-baseline.

5) **Verify**: On an empty DB, run Flyway with only `V100` (baseline folder). App should boot and show users/devices/app catalog/anomalies tables present. Apply repeatables (e.g., catalog seed) after baseline if needed.

6) **Roll forward existing DBs**: For dev/stage already at `V067`, set `baselineVersion=100` and `baselineOnMigrate=true`; Flyway will treat current schema as baseline and only apply new migrations beyond 100.

## Notes
- Devices: we continue to use the `assets` table in code; `V069__add_devices_table.sql` is preserved for compatibility but can be omitted from the baseline if you want to avoid duplication.
- Anomalies: `V068` formalizes the table created at runtime; baseline should include it to avoid runtime DDL.
- Do not delete old migrations until the baseline is adopted in all envs; just add the baseline and adjust Flyway config per-env.
- If you want catalog defaults during bootstrap, run repeatables from the main migrations folder (`R__seed_app_catalog.sql`) after the baseline migrate, or add a cleaned copy back into the baseline location once schema/id defaults align.
