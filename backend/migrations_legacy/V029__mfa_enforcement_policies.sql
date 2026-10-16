-- Migration: MFA Enforcement Policies
-- Date: 2025-12-02
-- Purpose: MFA enforcement and tracking for SOC 2 CC6.6 compliance

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- MFA enforcement policies
CREATE TABLE IF NOT EXISTS mfa_enforcement_policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL,
    policy_name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Enforcement scope
    enforcement_scope VARCHAR(50) NOT NULL, -- 'all_users', 'privileged_roles', 'specific_roles', 'specific_users'
    target_roles TEXT[], -- Array of role names if specific_roles
    target_users TEXT[], -- Array of user IDs if specific_users
    
    -- Enforcement type
    enforcement_type VARCHAR(50) DEFAULT 'required', -- 'required', 'recommended', 'optional'
    grace_period_days INTEGER DEFAULT 0,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(tenant_id, realm_name, policy_name)
);

CREATE INDEX idx_mfa_policies_tenant_realm ON mfa_enforcement_policies(tenant_id, realm_name);
CREATE INDEX idx_mfa_policies_active ON mfa_enforcement_policies(is_active);
CREATE INDEX idx_mfa_policies_scope ON mfa_enforcement_policies(enforcement_scope);

-- User MFA status (cached from Keycloak)
CREATE TABLE IF NOT EXISTS user_mfa_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL,
    user_id TEXT NOT NULL,
    user_email VARCHAR(255),
    user_name VARCHAR(255),
    
    -- MFA configuration
    mfa_enabled BOOLEAN DEFAULT FALSE,
    mfa_methods TEXT[], -- ['totp', 'webauthn', 'sms', 'email']
    mfa_configured_at TIMESTAMPTZ,
    
    -- Enforcement status
    enforcement_status VARCHAR(50) DEFAULT 'non_compliant', -- 'compliant', 'non_compliant', 'grace_period', 'exempt'
    applicable_policy_id UUID REFERENCES mfa_enforcement_policies(id),
    grace_period_expires_at TIMESTAMPTZ,
    exemption_reason TEXT,
    exempted_by TEXT,
    
    -- Tracking
    last_checked_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(tenant_id, realm_name, user_id)
);

CREATE INDEX idx_user_mfa_status_tenant_realm ON user_mfa_status(tenant_id, realm_name);
CREATE INDEX idx_user_mfa_status_user ON user_mfa_status(user_id);
CREATE INDEX idx_user_mfa_status_enabled ON user_mfa_status(mfa_enabled);
CREATE INDEX idx_user_mfa_status_enforcement ON user_mfa_status(enforcement_status);
CREATE INDEX idx_user_mfa_status_policy ON user_mfa_status(applicable_policy_id);

-- MFA compliance violations (for alerting)
CREATE TABLE IF NOT EXISTS mfa_compliance_violations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL,
    user_id TEXT NOT NULL,
    user_email VARCHAR(255),
    
    -- Violation details
    policy_id UUID REFERENCES mfa_enforcement_policies(id),
    violation_type VARCHAR(100), -- 'not_configured', 'grace_period_expired', 'disabled'
    violation_description TEXT,
    
    -- Status
    status VARCHAR(50) DEFAULT 'open', -- 'open', 'resolved', 'exempted'
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    
    -- Notifications
    notified_at TIMESTAMPTZ,
    notification_count INTEGER DEFAULT 0,
    
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_mfa_violations_tenant_realm ON mfa_compliance_violations(tenant_id, realm_name);
CREATE INDEX idx_mfa_violations_user ON mfa_compliance_violations(user_id);
CREATE INDEX idx_mfa_violations_status ON mfa_compliance_violations(status);
CREATE INDEX idx_mfa_violations_policy ON mfa_compliance_violations(policy_id);
CREATE INDEX idx_mfa_violations_detected ON mfa_compliance_violations(detected_at DESC);

-- Comments
COMMENT ON TABLE mfa_enforcement_policies IS 'MFA enforcement policies for SOC 2 CC6.6 compliance';
COMMENT ON COLUMN mfa_enforcement_policies.enforcement_type IS 'Enforcement level: required, recommended, optional';
COMMENT ON TABLE user_mfa_status IS 'Cached MFA status for users (synced from Keycloak)';
COMMENT ON TABLE mfa_compliance_violations IS 'MFA compliance violations for alerting and reporting';

