#!/usr/bin/env bash
set -euo pipefail

# Seed at least one scan per supported type for each tenant (idempotent by (tenant_id, scanner_id, target_ref)).
# Usage: DB_URL=postgresql://sg:sg@localhost:5432/sg TENANTS="demo_protect demo_protect_defend demo" ./scripts/seed_scans.sh

DB_URL=${DB_URL:-postgresql://sg:sg@localhost:5432/sg}
TENANTS=${TENANTS:-demo}

for slug in $TENANTS; do
  echo "🛰️ Seeding scans for tenant slug=${slug}"
  PGPASSWORD=${DB_PASSWORD:-} psql "$DB_URL" -v ON_ERROR_STOP=1 <<SQL
DO \$do\$
DECLARE
  t UUID;
  now_ts TIMESTAMP WITH TIME ZONE := now();
  scanners TEXT[] := ARRAY['cloud', 'network', 'webapp', 'endpoint', 'container', 'code'];
  sid_str TEXT;
  idx INT := 1;
  sid UUID;
BEGIN
  SELECT id INTO t FROM tenants WHERE slug = '${slug}' LIMIT 1;
  IF t IS NULL THEN
    RAISE EXCEPTION 'Tenant slug % not found', '${slug}';
  END IF;

  -- Clear previous seed rows for this tenant to stay idempotent
  DELETE FROM orchestration.scans WHERE tenant_id = t;

  FOREACH sid_str IN ARRAY scanners LOOP
    sid := uuid_generate_v4();
    INSERT INTO orchestration.scans (id, tenant_id, scanner_id, target_ref, status, created_at, updated_at, started_at, finished_at, summary)
    VALUES (
      sid,
      t,
      sid_str,
      format('%s-target-%s', sid_str, idx),
      'completed',
      now_ts - INTERVAL '1 hour',
      now_ts,
      now_ts - INTERVAL '50 minutes',
      now_ts - INTERVAL '45 minutes',
      jsonb_build_object('type', sid_str, 'result', 'passed', 'issues', jsonb_build_array())
    )
    ON CONFLICT (id) DO NOTHING;
    idx := idx + 1;
  END LOOP;
END \$do\$;
SQL
  echo "✅ Scans seeded for ${slug}"
done
