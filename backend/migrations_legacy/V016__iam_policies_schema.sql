-- Migration: IAM Policies Schema
-- Date: 2025-01-28
-- Purpose: Support policy editor with graphical DSL for IAM policies

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Policy templates (pre-built policies for common scenarios)
CREATE TABLE IF NOT EXISTS policy_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    policy_type VARCHAR(100) NOT NULL, -- 'signon', 'access', 'approval', 'sod'
    template_data JSONB NOT NULL, -- The policy DSL JSON
    is_system BOOLEAN DEFAULT FALSE, -- System templates cannot be deleted
    category VARCHAR(100), -- 'basic', 'advanced', 'compliance'
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_policy_templates_type ON policy_templates(policy_type);
CREATE INDEX idx_policy_templates_category ON policy_templates(category);

-- Policies (tenant-specific policy instances)
CREATE TABLE IF NOT EXISTS policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    policy_type VARCHAR(100) NOT NULL, -- 'signon', 'access', 'approval', 'sod'
    scope VARCHAR(100) NOT NULL DEFAULT 'tenant', -- 'tenant', 'app', 'entitlement'
    scope_id UUID, -- App ID or entitlement ID if scope is 'app' or 'entitlement'
    policy_data JSONB NOT NULL, -- The policy DSL JSON
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 100, -- Lower number = higher priority
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by TEXT, -- Keycloak user ID
    UNIQUE(tenant_id, name)
);

CREATE INDEX idx_policies_tenant ON policies(tenant_id);
CREATE INDEX idx_policies_type ON policies(policy_type);
CREATE INDEX idx_policies_scope ON policies(scope, scope_id);
CREATE INDEX idx_policies_active ON policies(is_active);
CREATE INDEX idx_policies_priority ON policies(priority);

-- Policy rules (individual rules within a policy)
CREATE TABLE IF NOT EXISTS policy_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_id UUID NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
    rule_id VARCHAR(255) NOT NULL, -- ID within the policy JSON
    name VARCHAR(255),
    description TEXT,
    conditions JSONB NOT NULL, -- Array of condition objects
    actions JSONB NOT NULL, -- Array of action objects
    priority INTEGER DEFAULT 100, -- Rule priority within policy
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_policy_rules_policy ON policy_rules(policy_id);
CREATE INDEX idx_policy_rules_active ON policy_rules(is_active);

-- Policy evaluations (audit log of policy evaluations)
CREATE TABLE IF NOT EXISTS policy_evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    policy_id UUID NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
    evaluation_type VARCHAR(100) NOT NULL, -- 'signon', 'access', 'approval'
    context JSONB NOT NULL, -- Evaluation context (user, resource, etc.)
    result VARCHAR(50) NOT NULL, -- 'allow', 'deny', 'step_up', 'require_approval'
    matched_rules JSONB, -- Which rules matched
    actions_taken JSONB, -- Actions that were executed
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_policy_evaluations_tenant ON policy_evaluations(tenant_id);
CREATE INDEX idx_policy_evaluations_policy ON policy_evaluations(policy_id);
CREATE INDEX idx_policy_evaluations_type ON policy_evaluations(evaluation_type);
CREATE INDEX idx_policy_evaluations_evaluated_at ON policy_evaluations(evaluated_at);

-- Policy conflicts (detected conflicts between policies)
CREATE TABLE IF NOT EXISTS policy_conflicts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    policy_id_1 UUID NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
    policy_id_2 UUID NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
    conflict_type VARCHAR(100) NOT NULL, -- 'overlapping', 'contradictory', 'circular'
    description TEXT,
    severity VARCHAR(50) DEFAULT 'medium', -- 'low', 'medium', 'high', 'critical'
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT -- Keycloak user ID
);

CREATE INDEX idx_policy_conflicts_tenant ON policy_conflicts(tenant_id);
CREATE INDEX idx_policy_conflicts_policy1 ON policy_conflicts(policy_id_1);
CREATE INDEX idx_policy_conflicts_policy2 ON policy_conflicts(policy_id_2);
CREATE INDEX idx_policy_conflicts_resolved ON policy_conflicts(resolved_at);

-- Comments for documentation
COMMENT ON TABLE policy_templates IS 'Pre-built policy templates for common scenarios';
COMMENT ON TABLE policies IS 'Tenant-specific policy instances (sign-on, access, approval, SoD)';
COMMENT ON TABLE policy_rules IS 'Individual rules within policies (for indexing and analysis)';
COMMENT ON TABLE policy_evaluations IS 'Audit log of policy evaluations';
COMMENT ON TABLE policy_conflicts IS 'Detected conflicts between policies';

COMMENT ON COLUMN policies.policy_data IS 'Policy DSL JSON with conditions and actions';
COMMENT ON COLUMN policies.scope IS 'Policy scope: tenant (global), app (per-app), entitlement (per-entitlement)';
COMMENT ON COLUMN policies.priority IS 'Lower number = higher priority (evaluated first)';
COMMENT ON COLUMN policy_rules.conditions IS 'Array of condition objects: [{type, op, value}, ...]';
COMMENT ON COLUMN policy_rules.actions IS 'Array of action objects: [{type, value, params}, ...]';
COMMENT ON COLUMN policy_evaluations.context IS 'Evaluation context: {user_id, resource, ip, country, risk_score, etc.}';
COMMENT ON COLUMN policy_evaluations.matched_rules IS 'Array of rule IDs that matched during evaluation';

