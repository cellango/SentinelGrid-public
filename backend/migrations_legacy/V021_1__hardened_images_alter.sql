-- Alter existing hardened_images table to match new schema
-- This migration updates the existing table structure

DO $$ 
BEGIN
    -- Rename os_flavor to os_type if needed
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hardened_images' AND column_name = 'os_flavor') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hardened_images' AND column_name = 'os_type') THEN
            ALTER TABLE hardened_images RENAME COLUMN os_flavor TO os_type;
        END IF;
    END IF;

    -- Add version column if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hardened_images' AND column_name = 'version') THEN
        ALTER TABLE hardened_images ADD COLUMN version VARCHAR(100);
        -- Generate version from existing data
        UPDATE hardened_images SET version = os_type || '-' || COALESCE(os_version, 'unknown') || '-cis-level' || cis_level::text || '-agent-' || COALESCE(agent_version, 'unknown') || '-build-' || id::text WHERE version IS NULL;
        ALTER TABLE hardened_images ALTER COLUMN version SET NOT NULL;
    END IF;

    -- Add scan_status if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hardened_images' AND column_name = 'scan_status') THEN
        ALTER TABLE hardened_images ADD COLUMN scan_status VARCHAR(20) NOT NULL DEFAULT 'pending';
    END IF;

    -- Add scan_date if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hardened_images' AND column_name = 'scan_date') THEN
        ALTER TABLE hardened_images ADD COLUMN scan_date TIMESTAMPTZ;
    END IF;

    -- Add scan_results if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hardened_images' AND column_name = 'scan_results') THEN
        ALTER TABLE hardened_images ADD COLUMN scan_results JSONB;
    END IF;

    -- Add vulnerability_count if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hardened_images' AND column_name = 'vulnerability_count') THEN
        ALTER TABLE hardened_images ADD COLUMN vulnerability_count JSONB DEFAULT '{"critical": 0, "high": 0, "medium": 0, "low": 0}';
    END IF;

    -- Add status if missing (map from existing fields)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hardened_images' AND column_name = 'status') THEN
        ALTER TABLE hardened_images ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'ready';
        -- Set status based on is_latest
        UPDATE hardened_images SET status = 'ready' WHERE is_latest = true;
    END IF;

    -- Add hardening_level if missing (map from cis_level)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hardened_images' AND column_name = 'hardening_level') THEN
        ALTER TABLE hardened_images ADD COLUMN hardening_level VARCHAR(50);
        UPDATE hardened_images SET hardening_level = 'cis-level' || cis_level::text WHERE hardening_level IS NULL;
    END IF;

    -- Add hardening_script_version if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hardened_images' AND column_name = 'hardening_script_version') THEN
        ALTER TABLE hardened_images ADD COLUMN hardening_script_version VARCHAR(50);
    END IF;

    -- Add build_number if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hardened_images' AND column_name = 'build_number') THEN
        ALTER TABLE hardened_images ADD COLUMN build_number INTEGER;
    END IF;

    -- Add customer_accounts if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hardened_images' AND column_name = 'customer_accounts') THEN
        ALTER TABLE hardened_images ADD COLUMN customer_accounts JSONB DEFAULT '[]';
    END IF;

    -- Add parent_image_version if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hardened_images' AND column_name = 'parent_image_version') THEN
        ALTER TABLE hardened_images ADD COLUMN parent_image_version VARCHAR(100);
    END IF;

    -- Add release_notes if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hardened_images' AND column_name = 'release_notes') THEN
        ALTER TABLE hardened_images ADD COLUMN release_notes TEXT;
    END IF;

    -- Add changelog if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hardened_images' AND column_name = 'changelog') THEN
        ALTER TABLE hardened_images ADD COLUMN changelog TEXT;
    END IF;
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_hardened_images_os_cloud ON hardened_images(os_type, os_version, cloud_provider);
CREATE INDEX IF NOT EXISTS idx_hardened_images_scan_status ON hardened_images(scan_status) WHERE scan_status = 'passed';
CREATE INDEX IF NOT EXISTS idx_hardened_images_status ON hardened_images(status);
CREATE INDEX IF NOT EXISTS idx_hardened_images_latest ON hardened_images(os_type, os_version, cloud_provider, is_latest) WHERE is_latest = true;
CREATE INDEX IF NOT EXISTS idx_hardened_images_agent_version ON hardened_images(agent_version);

-- Create image_version_history table
CREATE TABLE IF NOT EXISTS image_version_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id UUID NOT NULL REFERENCES hardened_images(id) ON DELETE CASCADE,
    parent_image_id UUID REFERENCES hardened_images(id) ON DELETE SET NULL,
    version_from VARCHAR(100),
    version_to VARCHAR(100),
    change_type VARCHAR(50),
    change_description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_image_version_history_image ON image_version_history(image_id);
CREATE INDEX IF NOT EXISTS idx_image_version_history_parent ON image_version_history(parent_image_id);

-- Add constraint for scan status (only if columns exist)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hardened_images' AND column_name = 'status') AND
       EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'hardened_images' AND column_name = 'scan_status') THEN
        -- Drop existing constraint if any
        ALTER TABLE hardened_images DROP CONSTRAINT IF EXISTS check_scan_status_for_distribution;
        -- Add constraint
        ALTER TABLE hardened_images ADD CONSTRAINT check_scan_status_for_distribution 
            CHECK (
                (status = 'ready' AND scan_status = 'passed') OR 
                (status != 'ready')
            );
    END IF;
END $$;

