-- FixGroups: actionable remediation units derived from scans
-- Note: keep tenant_id on all tables for isolation

CREATE TABLE IF NOT EXISTS fix_groups (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
    type VARCHAR(64) NOT NULL,                   -- patch_group | dependency_upgrade | base_image_rebuild | config_change | exception
    description TEXT,
    fixed_in_target TEXT,                        -- e.g., base image tag or package version
    priority VARCHAR(16),                        -- P0/P1/P2 or severity-derived
    sla_due TIMESTAMPTZ,
    status VARCHAR(32) DEFAULT 'open',           -- open | in_progress | pending_verify | closed
    owning_team_id TEXT,
    ai_guidance JSONB,                           -- optional AI-generated guidance (summary, steps, validation)
    ticket_id TEXT,
    ticket_status VARCHAR(32),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fix_groups_tenant ON fix_groups (tenant_id);
CREATE INDEX IF NOT EXISTS idx_fix_groups_scan ON fix_groups (scan_id);
CREATE INDEX IF NOT EXISTS idx_fix_groups_status ON fix_groups (status);
CREATE INDEX IF NOT EXISTS idx_fix_groups_sla ON fix_groups (sla_due);
CREATE INDEX IF NOT EXISTS idx_fix_groups_priority ON fix_groups (priority);

-- Link FixGroups to affected assets (asset_ref is a flexible string; can store hostname, image, repo, etc.)
CREATE TABLE IF NOT EXISTS fix_group_assets (
    fix_group_id UUID REFERENCES fix_groups(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    asset_ref TEXT NOT NULL,
    asset_type VARCHAR(64),
    environment VARCHAR(32),
    PRIMARY KEY (fix_group_id, asset_ref)
);

CREATE INDEX IF NOT EXISTS idx_fix_group_assets_tenant ON fix_group_assets (tenant_id);
CREATE INDEX IF NOT EXISTS idx_fix_group_assets_type ON fix_group_assets (asset_type);

-- Link FixGroups to CVEs they remediate
CREATE TABLE IF NOT EXISTS fix_group_cves (
    fix_group_id UUID REFERENCES fix_groups(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    cve_id TEXT NOT NULL,
    PRIMARY KEY (fix_group_id, cve_id)
);

CREATE INDEX IF NOT EXISTS idx_fix_group_cves_tenant ON fix_group_cves (tenant_id);
