-- Migration: Enhanced Platform Audit Logs
-- Date: 2025-12-02
-- Purpose: Complete audit trail for all platform operations (SOC 2 compliance)

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enhanced platform audit logs
CREATE TABLE IF NOT EXISTS platform_audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Actor information
    actor_user_id TEXT NOT NULL,
    actor_email VARCHAR(255),
    actor_roles TEXT[], -- Array of role names
    
    -- Action details
    action VARCHAR(100) NOT NULL, -- login, logout, config_change, role_change, user_create, etc.
    action_category VARCHAR(50), -- 'auth', 'iam', 'config', 'data', 'compliance'
    resource_type VARCHAR(100), -- 'user', 'role', 'policy', 'report', etc.
    resource_id TEXT,
    resource_name TEXT,
    
    -- State tracking (for reversibility and forensics)
    before_state JSONB,
    after_state JSONB,
    changes JSONB, -- Specific fields that changed
    
    -- Request context
    ip_address INET,
    user_agent TEXT,
    request_id TEXT, -- Correlation ID for distributed tracing
    session_id TEXT,
    
    -- Status
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    -- Additional metadata
    metadata JSONB,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance and compliance queries
CREATE INDEX idx_platform_audit_tenant_realm ON platform_audit_logs(tenant_id, realm_name);
CREATE INDEX idx_platform_audit_timestamp ON platform_audit_logs(timestamp DESC);
CREATE INDEX idx_platform_audit_actor ON platform_audit_logs(actor_user_id);
CREATE INDEX idx_platform_audit_action ON platform_audit_logs(action);
CREATE INDEX idx_platform_audit_category ON platform_audit_logs(action_category);
CREATE INDEX idx_platform_audit_resource ON platform_audit_logs(resource_type, resource_id);
CREATE INDEX idx_platform_audit_success ON platform_audit_logs(success);

-- Composite indexes for common compliance queries
CREATE INDEX idx_platform_audit_tenant_timestamp ON platform_audit_logs(tenant_id, timestamp DESC);
CREATE INDEX idx_platform_audit_actor_timestamp ON platform_audit_logs(actor_user_id, timestamp DESC);

-- Partition by month for better performance (example for future)
-- CREATE TABLE platform_audit_logs_2025_12 PARTITION OF platform_audit_logs
--     FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- Audit retention policies table
CREATE TABLE IF NOT EXISTS audit_retention_policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    policy_name VARCHAR(255) NOT NULL,
    
    -- Retention configuration
    hot_retention_days INTEGER DEFAULT 90, -- Days in PostgreSQL
    cold_retention_days INTEGER DEFAULT 365, -- Days in archive storage
    total_retention_days INTEGER DEFAULT 2555, -- 7 years for SOC 2
    
    -- Archive configuration
    archive_enabled BOOLEAN DEFAULT FALSE,
    archive_location TEXT, -- S3 path or similar
    
    -- Compliance requirements
    requires_immutability BOOLEAN DEFAULT TRUE,
    requires_encryption BOOLEAN DEFAULT TRUE,
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(tenant_id, policy_name)
);

-- Default retention policy for system
INSERT INTO audit_retention_policies (tenant_id, policy_name, hot_retention_days, cold_retention_days, total_retention_days)
VALUES (NULL, 'system_default', 365, 1825, 2555)
ON CONFLICT DO NOTHING;

-- Audit log statistics (for compliance reporting)
CREATE TABLE IF NOT EXISTS audit_log_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL,
    
    -- Time period
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    
    -- Statistics
    total_events BIGINT DEFAULT 0,
    successful_events BIGINT DEFAULT 0,
    failed_events BIGINT DEFAULT 0,
    
    -- By category
    auth_events BIGINT DEFAULT 0,
    iam_events BIGINT DEFAULT 0,
    config_events BIGINT DEFAULT 0,
    data_events BIGINT DEFAULT 0,
    compliance_events BIGINT DEFAULT 0,
    
    -- Unique actors
    unique_actors INTEGER DEFAULT 0,
    
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(tenant_id, realm_name, period_start, period_end)
);

CREATE INDEX idx_audit_stats_tenant_period ON audit_log_statistics(tenant_id, period_start DESC);

-- Comments for documentation
COMMENT ON TABLE platform_audit_logs IS 'Complete audit trail for all platform operations (SOC 2, NIST, HIPAA compliance)';
COMMENT ON COLUMN platform_audit_logs.before_state IS 'State before action (for rollback and forensics)';
COMMENT ON COLUMN platform_audit_logs.after_state IS 'State after action (for audit trail)';
COMMENT ON COLUMN platform_audit_logs.changes IS 'Specific fields that changed (for efficient auditing)';
COMMENT ON TABLE audit_retention_policies IS 'Audit log retention policies per tenant';
COMMENT ON TABLE audit_log_statistics IS 'Aggregated audit statistics for compliance reporting';

