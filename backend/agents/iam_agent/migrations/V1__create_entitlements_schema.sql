-- SentinelGrid IAM Database Schema
-- Migration V1: Create entitlements and governance tables
-- Managed by Flyway
-- Database: SentinelGridIAM

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- ENTITLEMENTS CORE TABLES
-- ============================================================================

-- Entitlements table
CREATE TABLE IF NOT EXISTS entitlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,  -- '*' for wildcard
    action VARCHAR(50) NOT NULL,
    granted_to_type VARCHAR(50) NOT NULL,  -- 'user', 'role', 'group'
    granted_to_id UUID NOT NULL,
    granted_to_name VARCHAR(255),  -- Denormalized for performance
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- 'active', 'expired', 'revoked', 'pending_review'
    granted_by UUID NOT NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    usage_count_90d INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    -- Note: tenant_id references tenants table in 'sg' database
    -- Foreign key constraint removed for cross-database compatibility
    -- Application-level validation ensures tenant_id exists
    CONSTRAINT unique_entitlement UNIQUE (
        tenant_id, resource_type, resource_id, action, 
        granted_to_type, granted_to_id
    ),
    CONSTRAINT valid_status CHECK (status IN ('active', 'expired', 'revoked', 'pending_review', 'suspended')),
    CONSTRAINT valid_granted_to_type CHECK (granted_to_type IN ('user', 'role', 'group'))
);

-- Indexes for entitlements
CREATE INDEX IF NOT EXISTS idx_entitlements_tenant ON entitlements(tenant_id);
CREATE INDEX IF NOT EXISTS idx_entitlements_granted_to ON entitlements(granted_to_type, granted_to_id);
CREATE INDEX IF NOT EXISTS idx_entitlements_resource ON entitlements(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_entitlements_status ON entitlements(status);
CREATE INDEX IF NOT EXISTS idx_entitlements_expires ON entitlements(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_entitlements_pattern ON entitlements(tenant_id, resource_type, action) WHERE resource_id = '*';

-- ============================================================================
-- GOVERNANCE & AUDIT TABLES
-- ============================================================================

-- Audit campaigns table
CREATE TABLE IF NOT EXISTS audit_campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    campaign_type VARCHAR(50) NOT NULL,  -- 'scheduled', 'on_demand', 'continuous', 'event_triggered'
    status VARCHAR(50) NOT NULL DEFAULT 'draft',  -- 'draft', 'scheduled', 'active', 'in_review', 'completed', 'cancelled'
    scope JSONB NOT NULL,  -- Filters for entitlements/users
    review_config JSONB NOT NULL,  -- Reviewer assignment, rules
    schedule JSONB NOT NULL,  -- Start/end dates, reminders
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    statistics JSONB DEFAULT '{}'::jsonb,  -- Progress statistics
    
    -- Note: tenant_id references tenants table in 'sg' database
    -- Foreign key constraint removed for cross-database compatibility
    -- Application-level validation ensures tenant_id exists
    CONSTRAINT valid_campaign_type CHECK (campaign_type IN ('scheduled', 'on_demand', 'continuous', 'event_triggered')),
    CONSTRAINT valid_campaign_status CHECK (status IN ('draft', 'scheduled', 'active', 'in_review', 'completed', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_campaigns_tenant ON audit_campaigns(tenant_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON audit_campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_schedule ON audit_campaigns(tenant_id, status, ((schedule->>'start_date')));

-- Certifications table
CREATE TABLE IF NOT EXISTS certifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL,
    entitlement_id UUID NOT NULL,
    certifier_id UUID NOT NULL,
    certifier_type VARCHAR(50) NOT NULL,  -- 'self', 'manager', 'admin', 'delegated'
    certifier_name VARCHAR(255),  -- Denormalized for performance
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- 'pending', 'approved', 'revoked', 'questioned', 'deferred'
    decision VARCHAR(50),  -- 'approve', 'revoke', 'question', 'defer', 'modify'
    justification TEXT,
    decision_date TIMESTAMPTZ,
    deadline TIMESTAMPTZ NOT NULL,
    escalated_to UUID,
    escalation_reason TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT fk_campaign FOREIGN KEY (campaign_id) REFERENCES audit_campaigns(id) ON DELETE CASCADE,
    CONSTRAINT fk_entitlement FOREIGN KEY (entitlement_id) REFERENCES entitlements(id) ON DELETE CASCADE,
    CONSTRAINT unique_certification UNIQUE (campaign_id, entitlement_id),
    CONSTRAINT valid_certifier_type CHECK (certifier_type IN ('self', 'manager', 'admin', 'delegated')),
    CONSTRAINT valid_certification_status CHECK (status IN ('pending', 'approved', 'revoked', 'questioned', 'deferred')),
    CONSTRAINT valid_decision CHECK (decision IN ('approve', 'revoke', 'question', 'defer', 'modify') OR decision IS NULL)
);

CREATE INDEX IF NOT EXISTS idx_certifications_campaign ON certifications(campaign_id);
CREATE INDEX IF NOT EXISTS idx_certifications_certifier ON certifications(certifier_id, status);
CREATE INDEX IF NOT EXISTS idx_certifications_deadline ON certifications(status, deadline) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_certifications_entitlement ON certifications(entitlement_id);

-- Audit schedule configuration table
CREATE TABLE IF NOT EXISTS audit_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    entitlement_pattern VARCHAR(500) NOT NULL,  -- Pattern to match entitlements (e.g., 'incident:*:write')
    frequency VARCHAR(50) NOT NULL,  -- 'monthly', 'quarterly', 'annual', 'continuous'
    reviewer_type VARCHAR(50) NOT NULL,  -- 'self', 'manager', 'admin'
    auto_revoke_days INTEGER NOT NULL DEFAULT 30,
    notification_config JSONB DEFAULT '{}'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Note: tenant_id references tenants table in 'sg' database
    -- Foreign key constraint removed for cross-database compatibility
    CONSTRAINT unique_schedule UNIQUE (tenant_id, entitlement_pattern),
    CONSTRAINT valid_frequency CHECK (frequency IN ('monthly', 'quarterly', 'annual', 'continuous')),
    CONSTRAINT valid_reviewer_type CHECK (reviewer_type IN ('self', 'manager', 'admin'))
);

CREATE INDEX IF NOT EXISTS idx_schedules_tenant ON audit_schedules(tenant_id);
CREATE INDEX IF NOT EXISTS idx_schedules_enabled ON audit_schedules(tenant_id, enabled) WHERE enabled = true;

-- ============================================================================
-- AUDIT LOG TABLES
-- ============================================================================

-- Entitlement audit log
CREATE TABLE IF NOT EXISTS entitlement_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entitlement_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,  -- 'granted', 'revoked', 'modified', 'expired', 'certified'
    performed_by UUID NOT NULL,
    performed_by_name VARCHAR(255),
    performed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    changes JSONB,  -- Before/after state
    reason TEXT,
    campaign_id UUID,  -- If action was part of a campaign
    certification_id UUID,  -- If action was part of a certification
    
    CONSTRAINT fk_entitlement FOREIGN KEY (entitlement_id) REFERENCES entitlements(id) ON DELETE CASCADE,
    CONSTRAINT fk_campaign FOREIGN KEY (campaign_id) REFERENCES audit_campaigns(id) ON DELETE SET NULL,
    CONSTRAINT fk_certification FOREIGN KEY (certification_id) REFERENCES certifications(id) ON DELETE SET NULL,
    CONSTRAINT valid_action CHECK (action IN ('granted', 'revoked', 'modified', 'expired', 'certified', 'suspended', 'reactivated'))
);

CREATE INDEX IF NOT EXISTS idx_audit_log_entitlement ON entitlement_audit_log(entitlement_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_performed_at ON entitlement_audit_log(performed_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_campaign ON entitlement_audit_log(campaign_id) WHERE campaign_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_log_performed_by ON entitlement_audit_log(performed_by);

-- Certification history (tracks all status changes)
CREATE TABLE IF NOT EXISTS certification_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    certification_id UUID NOT NULL,
    entitlement_id UUID NOT NULL,
    previous_status VARCHAR(50),
    new_status VARCHAR(50),
    decision VARCHAR(50),
    changed_by UUID NOT NULL,
    changed_by_name VARCHAR(255),
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reason TEXT,
    
    CONSTRAINT fk_certification FOREIGN KEY (certification_id) REFERENCES certifications(id) ON DELETE CASCADE,
    CONSTRAINT fk_entitlement FOREIGN KEY (entitlement_id) REFERENCES entitlements(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cert_history_certification ON certification_history(certification_id);
CREATE INDEX IF NOT EXISTS idx_cert_history_entitlement ON certification_history(entitlement_id);
CREATE INDEX IF NOT EXISTS idx_cert_history_changed_at ON certification_history(changed_at);

-- ============================================================================
-- ROLE MAPPING TABLES
-- ============================================================================

-- Role to entitlement pattern mapping
CREATE TABLE IF NOT EXISTS role_entitlement_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name VARCHAR(100) NOT NULL,  -- Keycloak role name (e.g., 'SOC_ANALYST')
    tenant_id UUID,  -- NULL for global patterns
    entitlement_pattern VARCHAR(500) NOT NULL,  -- e.g., 'incident:*:read@{tenant_id}'
    priority INTEGER DEFAULT 0,  -- For ordering when multiple patterns match
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Note: tenant_id references tenants table in 'sg' database (NULL for global patterns)
    -- Foreign key constraint removed for cross-database compatibility
    CONSTRAINT unique_role_pattern UNIQUE (role_name, tenant_id, entitlement_pattern)
);

CREATE INDEX IF NOT EXISTS idx_role_patterns_role ON role_entitlement_patterns(role_name, enabled);
CREATE INDEX IF NOT EXISTS idx_role_patterns_tenant ON role_entitlement_patterns(tenant_id) WHERE tenant_id IS NOT NULL;

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_entitlements_updated_at BEFORE UPDATE ON entitlements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_certifications_updated_at BEFORE UPDATE ON certifications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_audit_schedules_updated_at BEFORE UPDATE ON audit_schedules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_role_patterns_updated_at BEFORE UPDATE ON role_entitlement_patterns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically expire entitlements
CREATE OR REPLACE FUNCTION expire_entitlements()
RETURNS void AS $$
BEGIN
    UPDATE entitlements
    SET status = 'expired',
        updated_at = NOW()
    WHERE expires_at IS NOT NULL
      AND expires_at < NOW()
      AND status = 'active';
END;
$$ language 'plpgsql';

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE entitlements IS 'Core entitlements table storing fine-grained permissions';
COMMENT ON TABLE audit_campaigns IS 'Audit campaigns for access reviews and certifications';
COMMENT ON TABLE certifications IS 'Individual entitlement certifications within campaigns';
COMMENT ON TABLE audit_schedules IS 'Configuration for scheduled audit campaigns';
COMMENT ON TABLE entitlement_audit_log IS 'Complete audit trail of all entitlement changes';
COMMENT ON TABLE certification_history IS 'History of certification status changes';
COMMENT ON TABLE role_entitlement_patterns IS 'Mapping of Keycloak roles to entitlement patterns';

-- ============================================================================
-- NOTES
-- ============================================================================
-- This schema is in the SentinelGridIAM database, separate from the main 'sg' database.
-- Foreign keys to tenants table are removed for cross-database compatibility.
-- Application-level validation should verify tenant_id exists in sg.tenants table.
-- See V2 migration for tenant_references table for local validation support.

