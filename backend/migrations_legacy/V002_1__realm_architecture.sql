-- SentinelGrid V2 Realm Architecture Migration
-- PostgreSQL migration script
-- Adds support for multi-region, multi-realm architecture with Keycloak Organizations

-- ============================================================================
-- REALMS TABLE
-- ============================================================================
-- Tracks Keycloak realms (both multi-tenant and enterprise)
CREATE TABLE IF NOT EXISTS realms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    realm_name VARCHAR(255) UNIQUE NOT NULL,  -- e.g., "sg-mt-us-1", "sg-ent-acme"
    realm_type VARCHAR(50) NOT NULL CHECK (realm_type IN ('platform_admin', 'multi_tenant', 'enterprise')),
    region VARCHAR(50) NOT NULL,  -- "us", "eu", "ap", etc.
    shard_number INT,  -- NULL for enterprise realms, 1-N for multi-tenant realms
    tenant_count INT NOT NULL DEFAULT 0,  -- Current number of tenants in this realm
    max_tenants INT,  -- Capacity limit for multi-tenant realms (NULL = unlimited for enterprise)
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'full', 'maintenance', 'deprecated')),
    keycloak_realm_id VARCHAR(255),  -- Keycloak internal realm ID
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (region, realm_type, shard_number)  -- Prevent duplicate shards in same region
);

-- Index for realm lookup by region and type
CREATE INDEX IF NOT EXISTS idx_realms_region_type ON realms(region, realm_type, status);
CREATE INDEX IF NOT EXISTS idx_realms_tenant_count ON realms(tenant_count) WHERE realm_type = 'multi_tenant';

-- ============================================================================
-- CUSTOMERS TABLE
-- ============================================================================
-- Represents a customer/company (may have multiple organizations)
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,  -- Company name
    slug VARCHAR(255) UNIQUE NOT NULL,  -- URL-safe identifier
    has_dedicated_realm BOOLEAN NOT NULL DEFAULT false,
    realm_name VARCHAR(255),  -- NULL for shared realm customers, FK to realms.realm_name
    pricing_tier VARCHAR(50) NOT NULL CHECK (pricing_tier IN ('free', 'starter', 'professional', 'enterprise')),
    user_count INT NOT NULL DEFAULT 0,
    org_count INT NOT NULL DEFAULT 0,
    compliance_required BOOLEAN NOT NULL DEFAULT false,
    region VARCHAR(50) NOT NULL DEFAULT 'us',  -- Primary region for customer
    employee_count INT,  -- For pricing tier determination
    industry VARCHAR(100),  -- Optional: for analytics
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'churned')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (realm_name) REFERENCES realms(realm_name) ON DELETE SET NULL
);

-- Indexes for customer lookup
CREATE INDEX IF NOT EXISTS idx_customers_slug ON customers(slug);
CREATE INDEX IF NOT EXISTS idx_customers_pricing_tier ON customers(pricing_tier);
CREATE INDEX IF NOT EXISTS idx_customers_realm_name ON customers(realm_name);
CREATE INDEX IF NOT EXISTS idx_customers_region ON customers(region);

-- ============================================================================
-- ORGANIZATIONS TABLE
-- ============================================================================
-- For enterprise customers with multiple organizations (subsidiaries, departments, etc.)
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,  -- URL-safe identifier, unique within customer
    realm_name VARCHAR(255) NOT NULL,  -- Always set for orgs (may be shared or dedicated)
    keycloak_org_id VARCHAR(255),  -- Keycloak Organizations API ID (if using KC Orgs)
    keycloak_group_id VARCHAR(255),  -- Fallback: Keycloak group ID (if not using KC Orgs)
    parent_org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,  -- For hierarchical orgs
    org_type VARCHAR(50) NOT NULL DEFAULT 'business_unit' CHECK (org_type IN ('subsidiary', 'business_unit', 'department', 'team')),
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (customer_id, slug),  -- Slug unique within customer
    FOREIGN KEY (realm_name) REFERENCES realms(realm_name) ON DELETE RESTRICT
);

-- Indexes for organization lookup
CREATE INDEX IF NOT EXISTS idx_organizations_customer_id ON organizations(customer_id);
CREATE INDEX IF NOT EXISTS idx_organizations_realm_name ON organizations(realm_name);
CREATE INDEX IF NOT EXISTS idx_organizations_keycloak_org_id ON organizations(keycloak_org_id) WHERE keycloak_org_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_organizations_parent_org_id ON organizations(parent_org_id) WHERE parent_org_id IS NOT NULL;

-- ============================================================================
-- UPDATE TENANTS TABLE
-- ============================================================================
-- Extend existing tenants table with realm architecture support
ALTER TABLE tenants 
    ADD COLUMN IF NOT EXISTS realm_name VARCHAR(255),
    ADD COLUMN IF NOT EXISTS customer_id UUID,
    ADD COLUMN IF NOT EXISTS organization_id UUID,
    ADD COLUMN IF NOT EXISTS pricing_tier VARCHAR(50),
    ADD COLUMN IF NOT EXISTS realm_strategy VARCHAR(50) CHECK (realm_strategy IN ('shared', 'dedicated')),
    ADD COLUMN IF NOT EXISTS keycloak_org_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS keycloak_group_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS region VARCHAR(50) DEFAULT 'us';

-- Add foreign keys (if columns were just created)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'tenants_realm_name_fkey'
    ) THEN
        ALTER TABLE tenants ADD CONSTRAINT tenants_realm_name_fkey 
            FOREIGN KEY (realm_name) REFERENCES realms(realm_name) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'tenants_customer_id_fkey'
    ) THEN
        ALTER TABLE tenants ADD CONSTRAINT tenants_customer_id_fkey 
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'tenants_organization_id_fkey'
    ) THEN
        ALTER TABLE tenants ADD CONSTRAINT tenants_organization_id_fkey 
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Indexes for tenant lookup
CREATE INDEX IF NOT EXISTS idx_tenants_realm_name ON tenants(realm_name);
CREATE INDEX IF NOT EXISTS idx_tenants_customer_id ON tenants(customer_id);
CREATE INDEX IF NOT EXISTS idx_tenants_organization_id ON tenants(organization_id);
CREATE INDEX IF NOT EXISTS idx_tenants_region ON tenants(region);

-- ============================================================================
-- REALM CAPACITY TRACKING TABLE
-- ============================================================================
-- Tracks historical realm capacity for analytics and auto-scaling decisions
CREATE TABLE IF NOT EXISTS realm_capacity_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    realm_name VARCHAR(255) NOT NULL REFERENCES realms(realm_name) ON DELETE CASCADE,
    tenant_count INT NOT NULL,
    user_count INT NOT NULL,
    utilization_percent NUMERIC(5,2),  -- Calculated: (tenant_count / max_tenants) * 100
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for time-series queries
CREATE INDEX IF NOT EXISTS idx_realm_capacity_history_realm_time ON realm_capacity_history(realm_name, recorded_at DESC);

-- ============================================================================
-- TENANT PROVISIONING LOG TABLE
-- ============================================================================
-- Audit log for tenant provisioning events
CREATE TABLE IF NOT EXISTS tenant_provisioning_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN ('provision_start', 'provision_success', 'provision_failure', 'realm_assigned', 'org_created', 'user_created')),
    realm_name VARCHAR(255),
    details JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by VARCHAR(255)  -- User or system that triggered the event
);

-- Index for audit queries
CREATE INDEX IF NOT EXISTS idx_tenant_provisioning_log_tenant_id ON tenant_provisioning_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_provisioning_log_customer_id ON tenant_provisioning_log(customer_id);
CREATE INDEX IF NOT EXISTS idx_tenant_provisioning_log_created_at ON tenant_provisioning_log(created_at DESC);

-- ============================================================================
-- SEED INITIAL REALMS
-- ============================================================================
-- Create platform admin realm
INSERT INTO realms (realm_name, realm_type, region, shard_number, max_tenants, status)
VALUES ('sg-admin', 'platform_admin', 'us', NULL, NULL, 'active')
ON CONFLICT (realm_name) DO NOTHING;

-- Create initial multi-tenant realms for US and EU
INSERT INTO realms (realm_name, realm_type, region, shard_number, max_tenants, status)
VALUES 
    ('sg-mt-us-1', 'multi_tenant', 'us', 1, 1000, 'active'),
    ('sg-mt-eu-1', 'multi_tenant', 'eu', 1, 1000, 'active')
ON CONFLICT (realm_name) DO NOTHING;

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update realm tenant count
CREATE OR REPLACE FUNCTION update_realm_tenant_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE realms 
        SET tenant_count = tenant_count + 1,
            updated_at = now()
        WHERE realm_name = NEW.realm_name;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE realms 
        SET tenant_count = tenant_count - 1,
            updated_at = now()
        WHERE realm_name = OLD.realm_name;
    ELSIF TG_OP = 'UPDATE' AND OLD.realm_name IS DISTINCT FROM NEW.realm_name THEN
        -- Tenant moved to different realm
        UPDATE realms 
        SET tenant_count = tenant_count - 1,
            updated_at = now()
        WHERE realm_name = OLD.realm_name;
        
        UPDATE realms 
        SET tenant_count = tenant_count + 1,
            updated_at = now()
        WHERE realm_name = NEW.realm_name;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to maintain realm tenant count
DROP TRIGGER IF EXISTS trigger_update_realm_tenant_count ON tenants;
CREATE TRIGGER trigger_update_realm_tenant_count
    AFTER INSERT OR UPDATE OR DELETE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION update_realm_tenant_count();

-- Function to update customer counts
CREATE OR REPLACE FUNCTION update_customer_counts()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Update user count for customer
        UPDATE customers 
        SET user_count = (
            SELECT COUNT(*) 
            FROM tenants 
            WHERE customer_id = NEW.customer_id
        ),
        updated_at = now()
        WHERE id = NEW.customer_id;
        
        -- Update org count if organization is set
        IF NEW.organization_id IS NOT NULL THEN
            UPDATE customers 
            SET org_count = (
                SELECT COUNT(DISTINCT organization_id) 
                FROM tenants 
                WHERE customer_id = NEW.customer_id 
                AND organization_id IS NOT NULL
            ),
            updated_at = now()
            WHERE id = NEW.customer_id;
        END IF;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE customers 
        SET user_count = (
            SELECT COUNT(*) 
            FROM tenants 
            WHERE customer_id = OLD.customer_id
        ),
        org_count = (
            SELECT COUNT(DISTINCT organization_id) 
            FROM tenants 
            WHERE customer_id = OLD.customer_id 
            AND organization_id IS NOT NULL
        ),
        updated_at = now()
        WHERE id = OLD.customer_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to maintain customer counts
DROP TRIGGER IF EXISTS trigger_update_customer_counts ON tenants;
CREATE TRIGGER trigger_update_customer_counts
    AFTER INSERT OR DELETE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION update_customer_counts();

-- Function to check realm capacity before tenant assignment
CREATE OR REPLACE FUNCTION check_realm_capacity()
RETURNS TRIGGER AS $$
DECLARE
    v_max_tenants INT;
    v_current_count INT;
    v_realm_type VARCHAR(50);
BEGIN
    -- Get realm info
    SELECT max_tenants, tenant_count, realm_type 
    INTO v_max_tenants, v_current_count, v_realm_type
    FROM realms 
    WHERE realm_name = NEW.realm_name;
    
    -- Only check capacity for multi-tenant realms
    IF v_realm_type = 'multi_tenant' AND v_max_tenants IS NOT NULL THEN
        IF v_current_count >= v_max_tenants THEN
            RAISE EXCEPTION 'Realm % is at capacity (% / %)', 
                NEW.realm_name, v_current_count, v_max_tenants;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to check realm capacity before inserting tenant
DROP TRIGGER IF EXISTS trigger_check_realm_capacity ON tenants;
CREATE TRIGGER trigger_check_realm_capacity
    BEFORE INSERT ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION check_realm_capacity();

-- ============================================================================
-- VIEWS FOR CONVENIENT QUERIES
-- ============================================================================

-- View: Realm status with utilization
CREATE OR REPLACE VIEW realm_status AS
SELECT 
    r.id,
    r.realm_name,
    r.realm_type,
    r.region,
    r.shard_number,
    r.tenant_count,
    r.max_tenants,
    CASE 
        WHEN r.max_tenants IS NULL THEN NULL
        ELSE ROUND((r.tenant_count::NUMERIC / r.max_tenants::NUMERIC) * 100, 2)
    END AS utilization_percent,
    r.status,
    r.created_at,
    r.updated_at
FROM realms r;

-- View: Customer summary with realm info
CREATE OR REPLACE VIEW customer_summary AS
SELECT 
    c.id,
    c.name,
    c.slug,
    c.pricing_tier,
    c.has_dedicated_realm,
    c.realm_name,
    r.realm_type,
    c.user_count,
    c.org_count,
    c.region,
    c.compliance_required,
    c.status,
    c.created_at
FROM customers c
LEFT JOIN realms r ON c.realm_name = r.realm_name;

-- View: Tenant details with customer and organization info
CREATE OR REPLACE VIEW tenant_details AS
SELECT 
    t.id AS tenant_id,
    t.name AS tenant_name,
    t.slug AS tenant_slug,
    t.realm_name,
    t.region,
    c.id AS customer_id,
    c.name AS customer_name,
    c.pricing_tier,
    o.id AS organization_id,
    o.name AS organization_name,
    o.org_type,
    r.realm_type,
    t.status,
    t.created_at
FROM tenants t
LEFT JOIN customers c ON t.customer_id = c.id
LEFT JOIN organizations o ON t.organization_id = o.id
LEFT JOIN realms r ON t.realm_name = r.realm_name;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE realms IS 'Tracks Keycloak realms (platform admin, multi-tenant, and enterprise)';
COMMENT ON TABLE customers IS 'Represents a customer/company that may have multiple organizations';
COMMENT ON TABLE organizations IS 'Enterprise organizations (subsidiaries, departments) within a customer';
COMMENT ON TABLE realm_capacity_history IS 'Historical tracking of realm capacity for analytics';
COMMENT ON TABLE tenant_provisioning_log IS 'Audit log for tenant provisioning events';

COMMENT ON COLUMN realms.realm_type IS 'Type: platform_admin (sg-admin), multi_tenant (sg-mt-*), enterprise (sg-ent-*)';
COMMENT ON COLUMN realms.shard_number IS 'Shard number for multi-tenant realms (e.g., sg-mt-us-1 = shard 1)';
COMMENT ON COLUMN realms.max_tenants IS 'Maximum tenants for multi-tenant realms (NULL = unlimited for enterprise)';
COMMENT ON COLUMN customers.has_dedicated_realm IS 'True if customer has dedicated realm (enterprise tier or auto-upgraded)';
COMMENT ON COLUMN customers.compliance_required IS 'True if compliance requirements mandate dedicated realm';
COMMENT ON COLUMN organizations.keycloak_org_id IS 'Keycloak Organizations API ID (KC 25+)';
COMMENT ON COLUMN organizations.keycloak_group_id IS 'Fallback: Keycloak group ID if not using Organizations feature';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
