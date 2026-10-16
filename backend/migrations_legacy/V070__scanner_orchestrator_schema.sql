-- Scanner orchestrator schema: registry, scans, and enriched findings

CREATE TABLE IF NOT EXISTS scanner_registry (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    version             TEXT,
    image_digest        TEXT,
    parser              TEXT NOT NULL,
    default_limits      JSONB DEFAULT '{}'::jsonb,
    metadata            JSONB DEFAULT '{}'::jsonb,
    active              BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_scanner_registry_active ON scanner_registry (active);
CREATE INDEX IF NOT EXISTS idx_scanner_registry_name_version ON scanner_registry (name, version);

CREATE TABLE IF NOT EXISTS scans (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    scanner_id          TEXT,
    target_ref          TEXT,
    status              TEXT NOT NULL DEFAULT 'queued', -- queued | accepted | running | failed | completed
    started_at          TIMESTAMPTZ,
    finished_at         TIMESTAMPTZ,
    error               TEXT,
    raw_artifact_url    TEXT,
    summary             JSONB DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_scans_tenant ON scans (tenant_id);
CREATE INDEX IF NOT EXISTS idx_scans_status ON scans (status);
CREATE INDEX IF NOT EXISTS idx_scans_scanner ON scans (scanner_id);

-- Enrich findings with scan linkage and fingerprint/tags for dedup and filtering
ALTER TABLE findings ADD COLUMN IF NOT EXISTS scanner_id TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS scan_id UUID;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS fingerprint TEXT;
ALTER TABLE findings ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_findings_scan_id ON findings (scan_id);
CREATE INDEX IF NOT EXISTS idx_findings_scanner_id ON findings (scanner_id);
CREATE INDEX IF NOT EXISTS idx_findings_fingerprint ON findings (fingerprint);
