# Seeding Guide

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../RELEASE_SCOPE.md) first.


This repo now separates **schema migrations** (Flyway, schema-only) from **data seeds** (SQL files). Use these seed scripts to populate demo/global data after running migrations.

## Prerequisites
- Postgres reachable via `DB_URL` (e.g., `postgresql://sg:sg@localhost:5432/sg`).
- `psql` available (inside the compose network, use the `postgres` service host; on host, use `localhost`).

## Seed structure
- `seeds/global/seed_sg_admin.sql` — global catalog (policies/bundles, detections, playbooks, report templates) and the `sg_admin` tenant record.
- `seeds/tenant/demo_protect.sql` — Protect demo tenant (plan_tier=protect) + personas/content for Protect.
- `seeds/tenant/demo_protect_defend.sql` — Protect+Defend demo tenant content.
- `seeds/tenant/demo_protect_defend_comply.sql` — Protect+Defend+Comply demo tenant content.

## Scripts
- `scripts/seed_global.sh` — applies `seeds/global/seed_sg_admin.sql`.
- `scripts/seed_tenant.sh <seed-file>` — applies a specific tenant seed file (path relative to repo root).

Both scripts honor `DB_URL`; default is `postgresql://sg:sg@localhost:5432/sg`.

## Usage
```bash
# Global
DB_URL=postgresql://sg:sg@localhost:5432/sg ./scripts/seed_global.sh

# Tenants
DB_URL=postgresql://sg:sg@localhost:5432/sg ./scripts/seed_tenant.sh seeds/tenant/demo_protect.sql
DB_URL=postgresql://sg:sg@localhost:5432/sg ./scripts/seed_tenant.sh seeds/tenant/demo_protect_defend.sql
DB_URL=postgresql://sg:sg@localhost:5432/sg ./scripts/seed_tenant.sh seeds/tenant/demo_protect_defend_comply.sql
```

## Demo tenants & slugs
- `demo` (`ff1c2b60-1fd6-46d1-8458-b0484f5d58f8`): Protect+Defend+Comply. Seeds V007 scan/fix-groups, V122/V123 compliance reports, personas (admin/analyst/compliance) with IAM entitlements, and a baseline tenant authz policy.
- `demo2` (`b210c499-ea35-4e15-8b93-cd2446361d27`): Protect+Defend. Seeds V007-style scan/fix-groups, personas (admin/analyst/secops) with IAM entitlements, and a baseline tenant authz policy.
- `demo_protect` (`e4eddd32-5042-44ab-8cfc-cd2c841b633d`): Protect only. Seeds tenant + customer linkage, personas (admin/viewer) with IAM entitlements, and a baseline tenant authz policy.
- Global `sg_admin`: seeded via `seeds/global/seed_sg_admin.sql` (authorization policies from V128, built-in detections/playbooks from legacy V052, and shared report templates).

## Notes
- Seeds are intended to be idempotent (use `ON CONFLICT`/upserts).
- Schema migrations must remain data-free; move any data inserts from migrations into these seed files.
- Personas/role bindings for each demo tenant should be added to the respective seed SQL (Admin/Analyst/Reviewer etc.), respecting tenant_id/slug and plan_tier.

## Quick validation after seeding
Run these from `psql` (or wrap in a smoke script) to verify seed coverage:
- Plan tiers: `SELECT slug, plan_tier FROM tenants WHERE slug IN ('demo','demo2','demo_protect','sg_admin');`
- Scans seeded: `SELECT tenant_id, COUNT(*) FROM scans WHERE tenant_id IN (SELECT id FROM tenants WHERE slug IN ('demo','demo2')) GROUP BY tenant_id;`
- Compliance reports (should only exist for `demo`): `SELECT tenant_id, COUNT(*) FROM reporting.reports WHERE tenant_id IN (SELECT id FROM tenants WHERE slug='demo');`
- Personas/entitlements: `SELECT tenant_id, COUNT(*) FROM user_entitlements WHERE tenant_id IN (SELECT id FROM tenants WHERE slug IN ('demo','demo2','demo_protect')) GROUP BY tenant_id;`
- Alerts seeded: `SELECT tenant_id, COUNT(*) FROM security_ops.alerts WHERE tenant_id IN (SELECT id FROM tenants WHERE slug IN ('demo','demo2','demo_protect')) GROUP BY tenant_id;`

Alternatively, run the bundled smoke script (exits non-zero on mismatch):
```bash
DB_URL=postgresql://sg:sg@localhost:5432/sg ./scripts/validate_seeds.sh
```

## Flyway (schema-only)
To apply schema migrations while skipping the retired data-bearing versions, use:
```bash
DB_HOST=localhost DB_PORT=5432 DB_NAME=sg DB_USER=sg DB_PASSWORD=sg ./scripts/flyway_schema_only.sh
```
This uses `backend/migrations/flyway-schema-only.conf` to ignore the data migrations; run seeds afterward.
