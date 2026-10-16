-- Tool registry and async job queue schema
-- This migration introduces:
--  - tool_registry: catalog of scanning/enforcement tools
--  - jobs: lightweight async job queue (Postgres-backed)
--  - findings: normalized security findings
--  - assets: basic asset catalog for linking findings

-- tool_registry: describes tools and how they are invoked/parsing
CREATE TABLE IF NOT EXISTS tool_registry (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    category            TEXT NOT NULL,               -- e.g., cloud_security, git_security, app_security, ai, image_security
    job_types           TEXT[] NOT NULL DEFAULT '{}',-- job types this tool participates in
    image               TEXT NOT NULL,               -- container image
    command_template    JSONB NOT NULL,              -- array/structure of args with placeholders
    parser_key          TEXT NOT NULL,               -- parser identifier in code
    severity_map        JSONB DEFAULT '{}'::jsonb,   -- optional mapping of tool severities to platform severities
    tags                TEXT[] DEFAULT '{}',         -- e.g., [cspm, misconfiguration]
    status              TEXT NOT NULL DEFAULT 'active', -- active | experimental | deprecated
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tool_registry_category ON tool_registry (category);
CREATE INDEX IF NOT EXISTS idx_tool_registry_status ON tool_registry (status);

-- jobs: simple Postgres-backed queue
CREATE TABLE IF NOT EXISTS jobs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID,
    job_type        TEXT NOT NULL,                     -- e.g., cloud_initial_scan, git_daily_scan, ai_daily_summary
    status          TEXT NOT NULL DEFAULT 'queued',    -- queued | running | failed | completed
    payload         JSONB DEFAULT '{}'::jsonb,
    attempts        INT NOT NULL DEFAULT 0,
    max_attempts    INT NOT NULL DEFAULT 5,
    next_run_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    error           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_jobs_status_next_run ON jobs (status, next_run_at);
CREATE INDEX IF NOT EXISTS idx_jobs_tenant ON jobs (tenant_id);
CREATE INDEX IF NOT EXISTS idx_jobs_job_type ON jobs (job_type);

-- assets: lightweight catalog to link findings
CREATE TABLE IF NOT EXISTS assets (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL,
    asset_type      TEXT NOT NULL,                  -- cloud_account, cloud_db_instance, source_repo, image, app_url, etc.
    external_id     TEXT,                           -- provider-specific id/arn/url
    name            TEXT,
    metadata        JSONB DEFAULT '{}'::jsonb,
    last_seen_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ensure required columns exist if assets was created previously
ALTER TABLE assets ADD COLUMN IF NOT EXISTS tenant_id UUID;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS asset_type TEXT;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS external_id TEXT;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS name TEXT;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE assets ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_assets_tenant_type ON assets (tenant_id, asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_external_id ON assets (external_id);

-- findings: normalized findings from any tool
CREATE TABLE IF NOT EXISTS findings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL,
    source_tool     TEXT NOT NULL,                  -- e.g., prowler, trivy, gitleaks
    asset_id        UUID REFERENCES assets(id) ON DELETE SET NULL,
    asset_type      TEXT,                           -- duplicate for quick filtering
    severity        TEXT,                           -- critical/high/medium/low/info
    category        TEXT,                           -- cloud_misconfiguration, vuln, secret_exposure, etc.
    title           TEXT NOT NULL,
    description     TEXT,
    remediation     TEXT,
    evidence        JSONB DEFAULT '{}'::jsonb,
    raw_payload     JSONB,
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_findings_tenant ON findings (tenant_id);
CREATE INDEX IF NOT EXISTS idx_findings_asset ON findings (asset_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings (severity);
CREATE INDEX IF NOT EXISTS idx_findings_category ON findings (category);
CREATE INDEX IF NOT EXISTS idx_findings_detected_at ON findings (detected_at);
