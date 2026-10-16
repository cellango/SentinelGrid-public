-- SentinelGrid IAM Database Schema
-- Migration V2: Create tenant reference table for validation
-- Since we're in a separate database, we maintain a reference table
-- for tenant_id validation (can be synced from main sg database)

-- Tenant reference table (read-only cache from main database)
CREATE TABLE IF NOT EXISTS tenant_references (
    id UUID PRIMARY KEY,
    name TEXT,
    slug TEXT,
    status TEXT,
    last_synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_status CHECK (status IN ('active', 'inactive', 'suspended', 'pending'))
);

CREATE INDEX IF NOT EXISTS idx_tenant_ref_status ON tenant_references(status) WHERE status = 'active';

-- Function to validate tenant_id exists (for application use)
CREATE OR REPLACE FUNCTION validate_tenant_id(p_tenant_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM tenant_references 
        WHERE id = p_tenant_id AND status = 'active'
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- Comment
COMMENT ON TABLE tenant_references IS 'Reference table for tenant validation. Should be synced from main sg.tenants table.';
COMMENT ON FUNCTION validate_tenant_id IS 'Validates that a tenant_id exists and is active. Used for application-level validation since cross-database FK not possible.';

