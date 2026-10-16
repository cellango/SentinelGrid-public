-- Entitlement Agent Database Schema
-- Migration V3: Create access requests table
-- Managed by Flyway
-- Database: SentinelGridIAM

-- Access Requests table
CREATE TABLE IF NOT EXISTS access_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    requested_by UUID NOT NULL,  -- User requesting access
    requested_for UUID,  -- User to grant access to (can be same as requested_by)
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,  -- '*' for wildcard
    action VARCHAR(50) NOT NULL,
    justification TEXT NOT NULL,  -- Why access is needed
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- 'pending', 'approved', 'denied', 'cancelled'
    reviewer_id UUID,  -- Manager/admin who reviews
    reviewed_at TIMESTAMPTZ,
    review_comments TEXT,
    expires_at TIMESTAMPTZ,  -- Optional expiration for requested access
    entitlement_id UUID,  -- Created entitlement ID (if approved)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT valid_status CHECK (status IN ('pending', 'approved', 'denied', 'cancelled')),
    CONSTRAINT valid_resource_id CHECK (resource_id != '')
);

-- Indexes for access_requests
CREATE INDEX IF NOT EXISTS idx_access_requests_tenant ON access_requests(tenant_id);
CREATE INDEX IF NOT EXISTS idx_access_requests_requested_by ON access_requests(requested_by);
CREATE INDEX IF NOT EXISTS idx_access_requests_status ON access_requests(status);
CREATE INDEX IF NOT EXISTS idx_access_requests_reviewer ON access_requests(reviewer_id);
CREATE INDEX IF NOT EXISTS idx_access_requests_created_at ON access_requests(created_at DESC);

-- Access Request History (for timeline/audit)
CREATE TABLE IF NOT EXISTS access_request_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES access_requests(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,  -- 'created', 'submitted', 'approved', 'denied', 'cancelled', 'comment'
    performed_by UUID NOT NULL,
    performed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    comments TEXT,
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for access_request_history
CREATE INDEX IF NOT EXISTS idx_access_request_history_request_id ON access_request_history(request_id);
CREATE INDEX IF NOT EXISTS idx_access_request_history_performed_at ON access_request_history(performed_at DESC);

