SET search_path = public;

CREATE TABLE IF NOT EXISTS infrastructure_change_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    cloud_account_id UUID,
    scan_id UUID,
    fix_group_id UUID,
    provider VARCHAR(50) NOT NULL,
    action_type VARCHAR(100) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    server_id TEXT NOT NULL,
    firewall_id TEXT NOT NULL,
    scope_hash TEXT NOT NULL,
    pre_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    proposed_diff JSONB NOT NULL DEFAULT '{}'::jsonb,
    approval_required BOOLEAN NOT NULL DEFAULT true,
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    approval_notes TEXT,
    apply_requested_by TEXT,
    apply_started_at TIMESTAMPTZ,
    apply_completed_at TIMESTAMPTZ,
    apply_result JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_infra_change_requests_tenant_created
    ON infrastructure_change_requests (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_infra_change_requests_status
    ON infrastructure_change_requests (tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_infra_change_requests_cloud_account
    ON infrastructure_change_requests (cloud_account_id);
CREATE INDEX IF NOT EXISTS idx_infra_change_requests_scan
    ON infrastructure_change_requests (scan_id);

