-- Create scans table for per-tenant scan tracking
CREATE TABLE IF NOT EXISTS scans (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    scanner_id VARCHAR(128),
    target_ref TEXT,
    status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    summary JSONB,
    raw_artifact_url TEXT
);

CREATE INDEX IF NOT EXISTS idx_scans_tenant_created_at ON scans (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_scans_status ON scans (status);
