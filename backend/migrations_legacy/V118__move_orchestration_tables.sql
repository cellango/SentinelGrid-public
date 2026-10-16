-- Move orchestration-related tables into the orchestration schema.
-- This assumes V117 (schemas/roles) is applied.
-- Move tables first, then recreate foreign keys and indexes as needed.

-- Findings table is shared; it keeps its schema. Only indexes were added in V115.

-- 1) Move scanner_registry and scans into orchestration schema
ALTER TABLE IF EXISTS scanner_registry SET SCHEMA orchestration;
ALTER TABLE IF EXISTS scans SET SCHEMA orchestration;

-- 2) Recreate indexes under new schema (if not carried over automatically)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'idx_scanner_registry_active' AND n.nspname = 'orchestration'
  ) THEN
    CREATE INDEX idx_scanner_registry_active ON orchestration.scanner_registry (active);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'idx_scanner_registry_name_version' AND n.nspname = 'orchestration'
  ) THEN
    CREATE INDEX idx_scanner_registry_name_version ON orchestration.scanner_registry (name, version);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'idx_scans_tenant' AND n.nspname = 'orchestration'
  ) THEN
    CREATE INDEX idx_scans_tenant ON orchestration.scans (tenant_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'idx_scans_status' AND n.nspname = 'orchestration'
  ) THEN
    CREATE INDEX idx_scans_status ON orchestration.scans (status);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'idx_scans_scanner' AND n.nspname = 'orchestration'
  ) THEN
    CREATE INDEX idx_scans_scanner ON orchestration.scans (scanner_id);
  END IF;
END $$;

-- 3) Ensure default privileges apply to new schema (created in V117)
-- No-op here; defaults are already set for role sg in orchestration schema.
