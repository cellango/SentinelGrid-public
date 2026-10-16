-- Migration: Add Privileged Access Tables
-- Description: Manages privileged access requests, approvals, and JIT access
-- Date: 2025-01-28

CREATE TABLE IF NOT EXISTS privileged_access_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    requested_by UUID NOT NULL, -- User requesting access
    resource_type VARCHAR(100) NOT NULL, -- 'role', 'permission', 'resource'
    resource_id VARCHAR(255) NOT NULL,
    resource_name VARCHAR(255),
    reason TEXT NOT NULL,
    duration_hours INT DEFAULT 1, -- JIT access duration
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'approved', 'rejected', 'expired', 'revoked'
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by UUID,
    rejected_at TIMESTAMP,
    rejected_by UUID,
    rejection_reason TEXT,
    expires_at TIMESTAMP,
    revoked_at TIMESTAMP,
    revoked_by UUID,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_privileged_access_tenant ON privileged_access_requests(tenant_id);
CREATE INDEX IF NOT EXISTS idx_privileged_access_requested_by ON privileged_access_requests(requested_by);
CREATE INDEX IF NOT EXISTS idx_privileged_access_status ON privileged_access_requests(status);
CREATE INDEX IF NOT EXISTS idx_privileged_access_expires_at ON privileged_access_requests(expires_at);

-- Create table for approval workflows
CREATE TABLE IF NOT EXISTS privileged_access_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES privileged_access_requests(id) ON DELETE CASCADE,
    approver_id UUID NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    comments TEXT,
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for approvals
CREATE INDEX IF NOT EXISTS idx_privileged_access_approvals_request ON privileged_access_approvals(request_id);
CREATE INDEX IF NOT EXISTS idx_privileged_access_approvals_approver ON privileged_access_approvals(approver_id);

-- Create table for secrets
CREATE TABLE IF NOT EXISTS secrets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    secret_type VARCHAR(50) NOT NULL, -- 'password', 'api_key', 'token', 'certificate'
    encrypted_value TEXT NOT NULL, -- Encrypted secret value (stored in Vault in production)
    vault_path VARCHAR(500), -- Path in Vault
    access_control JSONB, -- Who can access this secret
    rotation_policy JSONB, -- Rotation schedule and rules
    last_rotated_at TIMESTAMP,
    next_rotation_at TIMESTAMP,
    created_by UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, name)
);

-- Create indexes for secrets
CREATE INDEX IF NOT EXISTS idx_secrets_tenant ON secrets(tenant_id);
CREATE INDEX IF NOT EXISTS idx_secrets_type ON secrets(secret_type);
CREATE INDEX IF NOT EXISTS idx_secrets_next_rotation ON secrets(next_rotation_at);

-- Create table for API keys
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID, -- Optional: user-specific key
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE, -- Hashed API key
    scopes JSONB, -- API scopes/permissions
    rate_limit_per_minute INT DEFAULT 60,
    rate_limit_per_hour INT DEFAULT 1000,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for API keys
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);

-- Add comments
COMMENT ON TABLE privileged_access_requests IS 'Privileged access requests with approval workflow';
COMMENT ON TABLE privileged_access_approvals IS 'Approval workflow for privileged access';
COMMENT ON TABLE secrets IS 'Shared secrets and credentials (encrypted)';
COMMENT ON TABLE api_keys IS 'API keys for programmatic access';

