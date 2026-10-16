-- Customer Cloud Accounts Schema
-- Tracks customer cloud provider accounts for image sharing

CREATE TABLE IF NOT EXISTS customer_cloud_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cloud_provider VARCHAR(20) NOT NULL,  -- aws, azure, gcp
    account_id TEXT,  -- AWS account ID
    subscription_id TEXT,  -- Azure subscription ID
    project_id TEXT,  -- GCP project ID
    regions JSONB DEFAULT '[]',  -- Array of regions: ["us-east-1", "us-west-2", ...]
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, inactive, suspended
    version_policy VARCHAR(20) DEFAULT 'latest',  -- latest, stable, pinned
    pinned_version VARCHAR(100),  -- If version_policy = 'pinned'
    metadata JSONB DEFAULT '{}',  -- Additional provider-specific metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, cloud_provider, account_id, subscription_id, project_id)
);

-- Indexes
CREATE INDEX idx_customer_cloud_accounts_tenant ON customer_cloud_accounts(tenant_id);
CREATE INDEX idx_customer_cloud_accounts_provider ON customer_cloud_accounts(cloud_provider);
CREATE INDEX idx_customer_cloud_accounts_status ON customer_cloud_accounts(status) WHERE status = 'active';

-- Track which images are shared with which customer accounts
CREATE TABLE IF NOT EXISTS image_customer_sharing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id UUID NOT NULL REFERENCES hardened_images(id) ON DELETE CASCADE,
    customer_account_id UUID NOT NULL REFERENCES customer_cloud_accounts(id) ON DELETE CASCADE,
    shared_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    share_status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, shared, failed
    error_message TEXT,
    UNIQUE(image_id, customer_account_id)
);

CREATE INDEX idx_image_customer_sharing_image ON image_customer_sharing(image_id);
CREATE INDEX idx_image_customer_sharing_account ON image_customer_sharing(customer_account_id);
CREATE INDEX idx_image_customer_sharing_status ON image_customer_sharing(share_status);

