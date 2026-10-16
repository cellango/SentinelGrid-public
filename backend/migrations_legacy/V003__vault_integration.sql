-- SentinelGrid V3 Vault Integration Migration
-- PostgreSQL migration script
-- Adds HashiCorp Vault integration with hierarchical multi-tenancy

-- ============================================================================
-- VAULT CUSTOMERS TABLE
-- ============================================================================
-- Tracks Vault configuration at customer level
CREATE TABLE IF NOT EXISTS vault_customers (
    customer_id UUID PRIMARY KEY REFERENCES customers(id) ON DELETE CASCADE,
    vault_path VARCHAR(255) UNIQUE NOT NULL,       -- e.g., "customers/{uuid}"
    vault_policy_name VARCHAR(255) NOT NULL,       -- e.g., "customer-{uuid}-policy"
    vault_entity_id VARCHAR(255) UNIQUE NOT NULL,  -- Vault entity ID
    
    -- Feature flags (customer-wide)
    kv_enabled BOOLEAN NOT NULL DEFAULT true,
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'disabled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_vault_customers_entity ON vault_customers(vault_entity_id);

-- ============================================================================
-- VAULT ORGANIZATIONS TABLE
-- ============================================================================
-- Tracks Vault configuration at organization level
CREATE TABLE IF NOT EXISTS vault_organizations (
    organization_id UUID PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    vault_path VARCHAR(255) UNIQUE NOT NULL,       -- e.g., "organizations/{uuid}"
    vault_policy_name VARCHAR(255) NOT NULL,       -- e.g., "org-{uuid}-policy"
    vault_entity_id VARCHAR(255) UNIQUE NOT NULL,  -- Vault entity ID
    
    -- Feature flags (organization-level)
    kv_enabled BOOLEAN NOT NULL DEFAULT true,
    transit_enabled BOOLEAN NOT NULL DEFAULT false,
    database_enabled BOOLEAN NOT NULL DEFAULT false,
    pki_enabled BOOLEAN NOT NULL DEFAULT false,
    
    -- Quotas (per organization)
    quota_secrets INT NOT NULL DEFAULT 5000,
    quota_secrets_used INT NOT NULL DEFAULT 0,
    quota_encryption_ops INT NOT NULL DEFAULT 500000,
    quota_encryption_used INT NOT NULL DEFAULT 0,
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'disabled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_vault_orgs_customer ON vault_organizations(customer_id);
CREATE INDEX idx_vault_orgs_entity ON vault_organizations(vault_entity_id);

-- ============================================================================
-- VAULT TENANTS TABLE
-- ============================================================================
-- Tracks Vault configuration at tenant level (THE isolation boundary)
CREATE TABLE IF NOT EXISTS vault_tenants (
    tenant_id UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    vault_path VARCHAR(255) UNIQUE NOT NULL,       -- e.g., "tenants/{uuid}"
    vault_policy_name VARCHAR(255) NOT NULL,       -- e.g., "tenant-{uuid}-policy"
    vault_entity_id VARCHAR(255) UNIQUE NOT NULL,  -- Vault entity ID
    vault_token_accessor VARCHAR(255),             -- For token revocation
    
    -- Feature flags (tenant-level)
    kv_enabled BOOLEAN NOT NULL DEFAULT true,
    transit_enabled BOOLEAN NOT NULL DEFAULT false,
    database_enabled BOOLEAN NOT NULL DEFAULT false,
    pki_enabled BOOLEAN NOT NULL DEFAULT false,
    
    -- Quotas (per tenant, inherited from org or customer)
    quota_secrets INT NOT NULL DEFAULT 1000,
    quota_secrets_used INT NOT NULL DEFAULT 0,
    quota_encryption_ops INT NOT NULL DEFAULT 100000,
    quota_encryption_used INT NOT NULL DEFAULT 0,
    quota_db_credentials INT NOT NULL DEFAULT 100,
    quota_db_credentials_used INT NOT NULL DEFAULT 0,
    quota_certificates INT NOT NULL DEFAULT 100,
    quota_certificates_used INT NOT NULL DEFAULT 0,
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'disabled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_vault_tenants_customer ON vault_tenants(customer_id);
CREATE INDEX idx_vault_tenants_org ON vault_tenants(organization_id);
CREATE INDEX idx_vault_tenants_entity ON vault_tenants(vault_entity_id);

-- ============================================================================
-- VAULT AUDIT LOG
-- ============================================================================
-- Comprehensive audit log for all Vault operations
CREATE TABLE IF NOT EXISTS vault_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    user_id VARCHAR(255),                          -- Keycloak user ID
    operation VARCHAR(100) NOT NULL,               -- e.g., "read_secret", "encrypt", "issue_cert"
    vault_path VARCHAR(500) NOT NULL,              -- Full Vault path accessed
    scope VARCHAR(50) NOT NULL CHECK (scope IN ('tenant', 'org', 'customer', 'platform')),
    success BOOLEAN NOT NULL,
    error_message TEXT,
    duration_ms INT,                               -- Operation duration
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for audit queries
CREATE INDEX idx_vault_audit_tenant_time ON vault_audit_log(tenant_id, created_at DESC);
CREATE INDEX idx_vault_audit_operation ON vault_audit_log(operation, created_at DESC);
CREATE INDEX idx_vault_audit_scope ON vault_audit_log(scope, created_at DESC);
CREATE INDEX idx_vault_audit_success ON vault_audit_log(success, created_at DESC) WHERE success = false;

-- ============================================================================
-- VAULT ACCESS GRANTS
-- ============================================================================
-- Granular permissions for Vault access (who can do what)
CREATE TABLE IF NOT EXISTS vault_access_grants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,                 -- Keycloak user ID
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Hierarchical access
    access_level VARCHAR(50) NOT NULL CHECK (access_level IN ('admin', 'write', 'read')),
    can_access_customer BOOLEAN NOT NULL DEFAULT false,    -- Can access customer-level secrets
    can_access_org BOOLEAN NOT NULL DEFAULT false,         -- Can access org-level secrets
    can_access_tenant BOOLEAN NOT NULL DEFAULT true,       -- Can access tenant-level secrets
    
    -- Specific permissions
    can_create_secrets BOOLEAN NOT NULL DEFAULT false,
    can_read_secrets BOOLEAN NOT NULL DEFAULT true,
    can_update_secrets BOOLEAN NOT NULL DEFAULT false,
    can_delete_secrets BOOLEAN NOT NULL DEFAULT false,
    can_use_encryption BOOLEAN NOT NULL DEFAULT false,
    can_generate_db_creds BOOLEAN NOT NULL DEFAULT false,
    can_issue_certificates BOOLEAN NOT NULL DEFAULT false,
    can_manage_policies BOOLEAN NOT NULL DEFAULT false,    -- Admin-level
    
    -- Audit
    granted_by VARCHAR(255),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_vault_access_user_tenant ON vault_access_grants(user_id, tenant_id);
CREATE INDEX idx_vault_access_level ON vault_access_grants(access_level);
CREATE INDEX idx_vault_access_active ON vault_access_grants(user_id, tenant_id) WHERE revoked_at IS NULL;

-- ============================================================================
-- VAULT QUOTA TRACKING
-- ============================================================================
-- Historical tracking of Vault usage for analytics and billing
CREATE TABLE IF NOT EXISTS vault_usage_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    
    -- Usage metrics
    secrets_count INT NOT NULL DEFAULT 0,
    encryption_operations INT NOT NULL DEFAULT 0,
    decryption_operations INT NOT NULL DEFAULT 0,
    db_credentials_generated INT NOT NULL DEFAULT 0,
    certificates_issued INT NOT NULL DEFAULT 0,
    
    -- Period
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_vault_usage_tenant_time ON vault_usage_history(tenant_id, period_start DESC);
CREATE INDEX idx_vault_usage_customer ON vault_usage_history(customer_id, period_start DESC);

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update quota usage
CREATE OR REPLACE FUNCTION update_vault_quota_usage()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.operation = 'create_secret' AND NEW.success = true THEN
        UPDATE vault_tenants 
        SET quota_secrets_used = quota_secrets_used + 1,
            updated_at = now()
        WHERE tenant_id = NEW.tenant_id;
    ELSIF TG_OP = 'INSERT' AND NEW.operation = 'delete_secret' AND NEW.success = true THEN
        UPDATE vault_tenants 
        SET quota_secrets_used = GREATEST(quota_secrets_used - 1, 0),
            updated_at = now()
        WHERE tenant_id = NEW.tenant_id;
    ELSIF TG_OP = 'INSERT' AND NEW.operation IN ('encrypt', 'decrypt') AND NEW.success = true THEN
        UPDATE vault_tenants 
        SET quota_encryption_used = quota_encryption_used + 1,
            updated_at = now()
        WHERE tenant_id = NEW.tenant_id;
    ELSIF TG_OP = 'INSERT' AND NEW.operation = 'generate_db_credentials' AND NEW.success = true THEN
        UPDATE vault_tenants 
        SET quota_db_credentials_used = quota_db_credentials_used + 1,
            updated_at = now()
        WHERE tenant_id = NEW.tenant_id;
    ELSIF TG_OP = 'INSERT' AND NEW.operation = 'issue_certificate' AND NEW.success = true THEN
        UPDATE vault_tenants 
        SET quota_certificates_used = quota_certificates_used + 1,
            updated_at = now()
        WHERE tenant_id = NEW.tenant_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update quota usage from audit log
DROP TRIGGER IF EXISTS trigger_update_vault_quota ON vault_audit_log;
CREATE TRIGGER trigger_update_vault_quota
    AFTER INSERT ON vault_audit_log
    FOR EACH ROW
    EXECUTE FUNCTION update_vault_quota_usage();

-- Function to check if tenant has exceeded quota
CREATE OR REPLACE FUNCTION check_vault_quota(
    p_tenant_id UUID,
    p_operation TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    v_quota_secrets INT;
    v_quota_used INT;
    v_quota_encryption INT;
    v_quota_encryption_used INT;
BEGIN
    -- Get quota limits and current usage
    SELECT 
        quota_secrets,
        quota_secrets_used,
        quota_encryption_ops,
        quota_encryption_used
    INTO 
        v_quota_secrets,
        v_quota_used,
        v_quota_encryption,
        v_quota_encryption_used
    FROM vault_tenants
    WHERE tenant_id = p_tenant_id;
    
    -- Check if tenant exists
    IF NOT FOUND THEN
        RETURN false;
    END IF;
    
    -- Check quota based on operation type
    IF p_operation = 'create_secret' THEN
        RETURN v_quota_used < v_quota_secrets;
    ELSIF p_operation IN ('encrypt', 'decrypt') THEN
        RETURN v_quota_encryption_used < v_quota_encryption;
    ELSE
        -- For other operations, allow by default (no quota limit)
        RETURN true;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View: Vault tenant status with quota information
CREATE OR REPLACE VIEW vault_tenant_status AS
SELECT 
    vt.tenant_id,
    t.name AS tenant_name,
    t.slug AS tenant_slug,
    o.name AS organization_name,
    c.name AS customer_name,
    vt.vault_path,
    vt.kv_enabled,
    vt.transit_enabled,
    vt.database_enabled,
    vt.pki_enabled,
    vt.quota_secrets,
    vt.quota_secrets_used,
    ROUND((vt.quota_secrets_used::NUMERIC / vt.quota_secrets::NUMERIC) * 100, 2) AS secrets_utilization_percent,
    vt.quota_encryption_ops,
    vt.quota_encryption_used,
    vt.status,
    vt.created_at
FROM vault_tenants vt
JOIN tenants t ON vt.tenant_id = t.id
LEFT JOIN organizations o ON vt.organization_id = o.id
LEFT JOIN customers c ON vt.customer_id = c.id;

-- View: Vault usage summary by customer
CREATE OR REPLACE VIEW vault_usage_by_customer AS
SELECT 
    c.id AS customer_id,
    c.name AS customer_name,
    c.pricing_tier,
    COUNT(DISTINCT vt.tenant_id) AS tenants_with_vault,
    SUM(vt.quota_secrets_used) AS total_secrets,
    SUM(vt.quota_encryption_used) AS total_encryption_ops,
    SUM(vt.quota_certificates_used) AS total_certificates
FROM customers c
LEFT JOIN vault_tenants vt ON vt.customer_id = c.id
WHERE vt.status = 'active'
GROUP BY c.id, c.name, c.pricing_tier;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE vault_customers IS 'Customer-level Vault configuration and quotas';
COMMENT ON TABLE vault_organizations IS 'Organization-level Vault configuration and quotas';
COMMENT ON TABLE vault_tenants IS 'Tenant-level Vault configuration - THE isolation boundary';
COMMENT ON TABLE vault_audit_log IS 'Comprehensive audit log for all Vault operations';
COMMENT ON TABLE vault_access_grants IS 'Granular access control for Vault operations';
COMMENT ON TABLE vault_usage_history IS 'Historical Vault usage for analytics and billing';

COMMENT ON COLUMN vault_tenants.vault_path IS 'Vault path prefix: tenants/{uuid}';
COMMENT ON COLUMN vault_tenants.vault_policy_name IS 'Tenant-specific policy name';
COMMENT ON COLUMN vault_tenants.vault_entity_id IS 'Vault entity ID for token generation';
COMMENT ON COLUMN vault_tenants.vault_token_accessor IS 'Token accessor for revocation';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

