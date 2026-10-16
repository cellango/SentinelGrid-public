-- Alter existing customer_cloud_accounts table to match new schema
-- This migration updates the existing table structure

DO $$ 
BEGIN
    -- Add version_policy if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'customer_cloud_accounts' AND column_name = 'version_policy') THEN
        ALTER TABLE customer_cloud_accounts ADD COLUMN version_policy VARCHAR(20) DEFAULT 'latest';
    END IF;

    -- Add pinned_version if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'customer_cloud_accounts' AND column_name = 'pinned_version') THEN
        ALTER TABLE customer_cloud_accounts ADD COLUMN pinned_version VARCHAR(100);
    END IF;

    -- Add metadata if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'customer_cloud_accounts' AND column_name = 'metadata') THEN
        ALTER TABLE customer_cloud_accounts ADD COLUMN metadata JSONB DEFAULT '{}';
    END IF;
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_customer_cloud_accounts_tenant ON customer_cloud_accounts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_customer_cloud_accounts_provider ON customer_cloud_accounts(cloud_provider);
CREATE INDEX IF NOT EXISTS idx_customer_cloud_accounts_status ON customer_cloud_accounts(status) WHERE status = 'active';

-- Create image_customer_sharing table
CREATE TABLE IF NOT EXISTS image_customer_sharing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id UUID NOT NULL REFERENCES hardened_images(id) ON DELETE CASCADE,
    customer_account_id UUID NOT NULL REFERENCES customer_cloud_accounts(id) ON DELETE CASCADE,
    shared_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    share_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    UNIQUE(image_id, customer_account_id)
);

CREATE INDEX IF NOT EXISTS idx_image_customer_sharing_image ON image_customer_sharing(image_id);
CREATE INDEX IF NOT EXISTS idx_image_customer_sharing_account ON image_customer_sharing(customer_account_id);
CREATE INDEX IF NOT EXISTS idx_image_customer_sharing_status ON image_customer_sharing(share_status);

