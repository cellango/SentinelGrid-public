-- Migration: IAM Portal Schema
-- Date: 2025-01-28
-- Purpose: Support frictionless IAM portal with apps, entitlements, access profiles, and requests

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Apps table (integrated applications)
CREATE TABLE IF NOT EXISTS apps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    app_type VARCHAR(100) NOT NULL, -- 'sentinelgrid', 'github', 'aws', 'jira', 'slack', etc.
    icon_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    config JSONB, -- App-specific configuration
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, name)
);

CREATE INDEX idx_apps_tenant ON apps(tenant_id);
CREATE INDEX idx_apps_type ON apps(app_type);
CREATE INDEX idx_apps_active ON apps(is_active);

-- Entitlements table (logical permissions/roles)
CREATE TABLE IF NOT EXISTS entitlements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    app_id UUID NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    entitlement_type VARCHAR(100) NOT NULL, -- 'role', 'permission', 'access_level'
    is_privileged BOOLEAN DEFAULT FALSE, -- Requires approval for privileged roles
    requires_mfa BOOLEAN DEFAULT FALSE,
    risk_level VARCHAR(50) DEFAULT 'low', -- 'low', 'medium', 'high', 'critical'
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, app_id, name)
);

CREATE INDEX idx_entitlements_tenant ON entitlements(tenant_id);
CREATE INDEX idx_entitlements_app ON entitlements(app_id);
CREATE INDEX idx_entitlements_privileged ON entitlements(is_privileged);
CREATE INDEX idx_entitlements_risk ON entitlements(risk_level);

-- Entitlement mappings (maps entitlements to Keycloak groups/roles)
CREATE TABLE IF NOT EXISTS entitlement_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entitlement_id UUID NOT NULL REFERENCES entitlements(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL, -- Keycloak realm
    keycloak_group_id TEXT, -- Keycloak group ID (optional)
    keycloak_group_name TEXT, -- Keycloak group name (optional)
    keycloak_role_name TEXT, -- Keycloak realm or client role name
    keycloak_client_id TEXT, -- Keycloak client ID if client role
    provisioning_config JSONB, -- External provisioning config (e.g., GitHub API calls)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_entitlement_mappings_entitlement ON entitlement_mappings(entitlement_id);
CREATE INDEX idx_entitlement_mappings_tenant ON entitlement_mappings(tenant_id);
CREATE INDEX idx_entitlement_mappings_realm ON entitlement_mappings(realm_name);

-- Access profiles (bundles of entitlements)
CREATE TABLE IF NOT EXISTS access_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE, -- Default profile for new users
    is_system BOOLEAN DEFAULT FALSE, -- System profile (cannot be deleted)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, name)
);

CREATE INDEX idx_access_profiles_tenant ON access_profiles(tenant_id);
CREATE INDEX idx_access_profiles_default ON access_profiles(is_default);

-- Access profile entitlements (many-to-many)
CREATE TABLE IF NOT EXISTS access_profile_entitlements (
    access_profile_id UUID NOT NULL REFERENCES access_profiles(id) ON DELETE CASCADE,
    entitlement_id UUID NOT NULL REFERENCES entitlements(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (access_profile_id, entitlement_id)
);

CREATE INDEX idx_profile_entitlements_profile ON access_profile_entitlements(access_profile_id);
CREATE INDEX idx_profile_entitlements_entitlement ON access_profile_entitlements(entitlement_id);

-- User entitlements (current assignments)
CREATE TABLE IF NOT EXISTS user_entitlements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL, -- Keycloak user ID
    entitlement_id UUID NOT NULL REFERENCES entitlements(id) ON DELETE CASCADE,
    granted_by TEXT, -- Keycloak user ID of grantor
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ, -- Optional expiration
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'revoked', 'expired'
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_user_entitlements_tenant ON user_entitlements(tenant_id);
CREATE INDEX idx_user_entitlements_user ON user_entitlements(user_id);
CREATE INDEX idx_user_entitlements_entitlement ON user_entitlements(entitlement_id);
CREATE INDEX idx_user_entitlements_status ON user_entitlements(status);
CREATE INDEX idx_user_entitlements_expires ON user_entitlements(expires_at);

-- Access requests (self-service requests)
CREATE TABLE IF NOT EXISTS access_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    requested_by TEXT NOT NULL, -- Keycloak user ID
    entitlement_id UUID NOT NULL REFERENCES entitlements(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    duration_days INTEGER, -- Temporary access duration (NULL = permanent)
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'approved', 'denied', 'cancelled'
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT, -- Keycloak user ID of approver
    resolution_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_access_requests_tenant ON access_requests(tenant_id);
CREATE INDEX idx_access_requests_user ON access_requests(requested_by);
CREATE INDEX idx_access_requests_entitlement ON access_requests(entitlement_id);
CREATE INDEX idx_access_requests_status ON access_requests(status);
CREATE INDEX idx_access_requests_requested_at ON access_requests(requested_at);

-- Approvals (approval workflow)
CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    access_request_id UUID NOT NULL REFERENCES access_requests(id) ON DELETE CASCADE,
    approver_id TEXT NOT NULL, -- Keycloak user ID
    approver_type VARCHAR(50) NOT NULL, -- 'manager', 'app_owner', 'admin'
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'approved', 'denied'
    notes TEXT,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_approvals_request ON approvals(access_request_id);
CREATE INDEX idx_approvals_approver ON approvals(approver_id);
CREATE INDEX idx_approvals_status ON approvals(status);

-- IAM audit log (all IAM changes)
CREATE TABLE IF NOT EXISTS iam_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL,
    action VARCHAR(100) NOT NULL, -- 'user_created', 'entitlement_granted', 'entitlement_revoked', 'access_requested', 'access_approved', etc.
    actor_user_id TEXT, -- Keycloak user ID
    actor_email VARCHAR(255),
    target_user_id TEXT, -- Keycloak user ID (if action affects a user)
    target_entitlement_id UUID REFERENCES entitlements(id) ON DELETE SET NULL,
    target_access_request_id UUID REFERENCES access_requests(id) ON DELETE SET NULL,
    details JSONB, -- Additional context
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_iam_audit_tenant ON iam_audit_log(tenant_id);
CREATE INDEX idx_iam_audit_realm ON iam_audit_log(realm_name);
CREATE INDEX idx_iam_audit_action ON iam_audit_log(action);
CREATE INDEX idx_iam_audit_actor ON iam_audit_log(actor_user_id);
CREATE INDEX idx_iam_audit_target_user ON iam_audit_log(target_user_id);
CREATE INDEX idx_iam_audit_created ON iam_audit_log(created_at);

-- Comments for documentation
COMMENT ON TABLE apps IS 'Integrated applications (SentinelGrid, GitHub, AWS, Jira, etc.)';
COMMENT ON TABLE entitlements IS 'Logical permissions/roles that map to Keycloak groups/roles';
COMMENT ON TABLE entitlement_mappings IS 'Maps entitlements to Keycloak groups/roles and external provisioning';
COMMENT ON TABLE access_profiles IS 'Bundles of entitlements (e.g., "Standard Employee", "Developer")';
COMMENT ON TABLE access_profile_entitlements IS 'Many-to-many relationship between access profiles and entitlements';
COMMENT ON TABLE user_entitlements IS 'Current entitlement assignments to users';
COMMENT ON TABLE access_requests IS 'Self-service access requests from users';
COMMENT ON TABLE approvals IS 'Approval workflow for access requests';
COMMENT ON TABLE iam_audit_log IS 'Audit log for all IAM operations';

COMMENT ON COLUMN entitlements.is_privileged IS 'Requires approval for privileged roles';
COMMENT ON COLUMN entitlements.risk_level IS 'Risk level: low, medium, high, critical';
COMMENT ON COLUMN entitlement_mappings.provisioning_config IS 'External provisioning config (e.g., GitHub API calls)';
COMMENT ON COLUMN access_profiles.is_default IS 'Default profile assigned to new users';
COMMENT ON COLUMN access_profiles.is_system IS 'System profile that cannot be deleted';
COMMENT ON COLUMN user_entitlements.expires_at IS 'Optional expiration date for temporary access';
COMMENT ON COLUMN access_requests.duration_days IS 'Temporary access duration (NULL = permanent)';
COMMENT ON COLUMN approvals.approver_type IS 'Type of approver: manager, app_owner, admin';

