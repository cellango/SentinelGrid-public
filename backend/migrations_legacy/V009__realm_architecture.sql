-- Migration: Realm Architecture Support
-- Date: 2025-11-30
-- Purpose: Support hybrid multi-realm architecture with customers, organizations, and audit logging

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Customers table (enhanced for realm architecture)
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    realm_name VARCHAR(255) UNIQUE, -- NULL for shared realm
    has_dedicated_realm BOOLEAN DEFAULT FALSE,
    tier VARCHAR(50) DEFAULT 'smb', -- 'smb', 'midmarket', 'enterprise'
    pricing_tier VARCHAR(50) DEFAULT 'starter', -- 'free', 'starter', 'professional', 'enterprise'
    user_count INTEGER DEFAULT 0,
    org_count INTEGER DEFAULT 0,
    compliance_required BOOLEAN DEFAULT FALSE,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_customers_realm ON customers(realm_name);
CREATE INDEX idx_customers_tier ON customers(tier);
CREATE INDEX idx_customers_pricing_tier ON customers(pricing_tier);

-- Organizations table (for enterprise customers with multiple orgs)
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    realm_name VARCHAR(255) UNIQUE NOT NULL,
    slug VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(customer_id, slug)
);

CREATE INDEX idx_organizations_customer ON organizations(customer_id);
CREATE INDEX idx_organizations_realm ON organizations(realm_name);
CREATE INDEX idx_organizations_slug ON organizations(slug);

-- User-Tenant mapping (for tenant_id lookup and realm association)
CREATE TABLE IF NOT EXISTS user_tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL, -- Keycloak user ID (sub claim)
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL, -- For quick lookup
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, tenant_id)
);

CREATE INDEX idx_user_tenants_user ON user_tenants(user_id);
CREATE INDEX idx_user_tenants_tenant ON user_tenants(tenant_id);
CREATE INDEX idx_user_tenants_customer ON user_tenants(customer_id);
CREATE INDEX idx_user_tenants_org ON user_tenants(organization_id);
CREATE INDEX idx_user_tenants_realm ON user_tenants(realm_name);

-- Realm audit log (security and compliance)
CREATE TABLE IF NOT EXISTS realm_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    realm_name VARCHAR(255) NOT NULL,
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL, -- 'create', 'update', 'delete', 'user_login', 'user_logout', 'user_signup', 'token_refresh'
    actor_user_id TEXT, -- Keycloak user ID
    actor_email VARCHAR(255),
    details JSONB, -- Additional context (IP, user agent, etc.)
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_realm_audit_realm ON realm_audit_log(realm_name);
CREATE INDEX idx_realm_audit_customer ON realm_audit_log(customer_id);
CREATE INDEX idx_realm_audit_org ON realm_audit_log(organization_id);
CREATE INDEX idx_realm_audit_action ON realm_audit_log(action);
CREATE INDEX idx_realm_audit_created ON realm_audit_log(created_at);
CREATE INDEX idx_realm_audit_actor ON realm_audit_log(actor_user_id);

-- Add customer_id to tenants table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tenants' AND column_name = 'customer_id'
    ) THEN
        ALTER TABLE tenants ADD COLUMN customer_id UUID REFERENCES customers(id) ON DELETE SET NULL;
        CREATE INDEX idx_tenants_customer ON tenants(customer_id);
    END IF;
END $$;

-- Add organization_id to tenants table if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tenants' AND column_name = 'organization_id'
    ) THEN
        ALTER TABLE tenants ADD COLUMN organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL;
        CREATE INDEX idx_tenants_organization ON tenants(organization_id);
    END IF;
END $$;

-- Comments for documentation
COMMENT ON TABLE customers IS 'Customer accounts with realm strategy (shared or dedicated)';
COMMENT ON TABLE organizations IS 'Organizations within enterprise customers (each gets dedicated realm)';
COMMENT ON TABLE user_tenants IS 'Mapping between Keycloak users and tenants with realm association';
COMMENT ON TABLE realm_audit_log IS 'Audit log for all realm-related security events';

COMMENT ON COLUMN customers.realm_name IS 'Keycloak realm name (NULL for shared realm, set for dedicated)';
COMMENT ON COLUMN customers.has_dedicated_realm IS 'Whether customer has dedicated Keycloak realm';
COMMENT ON COLUMN customers.tier IS 'Customer tier: smb, midmarket, enterprise';
COMMENT ON COLUMN customers.pricing_tier IS 'Pricing tier: free, starter, professional, enterprise';
COMMENT ON COLUMN organizations.realm_name IS 'Dedicated Keycloak realm name for this organization';
COMMENT ON COLUMN user_tenants.realm_name IS 'Keycloak realm where user exists';
COMMENT ON COLUMN realm_audit_log.action IS 'Action type: create, update, delete, user_login, user_logout, user_signup, token_refresh';

