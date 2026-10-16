-- Hardened Images Registry Schema
-- Tracks built and distributed hardened OS images

CREATE TABLE IF NOT EXISTS hardened_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(100) NOT NULL,  -- Semantic version or build identifier
    os_type VARCHAR(50) NOT NULL,  -- amazon-linux-2, ubuntu-22.04, rhel-8, etc.
    os_version VARCHAR(50) NOT NULL,  -- 2023, 22.04, 8, etc.
    cloud_provider VARCHAR(20) NOT NULL,  -- aws, azure, gcp
    image_id TEXT NOT NULL,  -- AMI ID, Azure Image ID, GCP Image ID
    region VARCHAR(50) NOT NULL,
    agent_version VARCHAR(50) NOT NULL REFERENCES agent_versions(version) ON DELETE RESTRICT,
    hardening_level VARCHAR(50) NOT NULL,  -- cis-level1, cis-level2, custom
    hardening_script_version VARCHAR(50),  -- Version of hardening scripts used
    build_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_number INTEGER,  -- Sequential build counter
    status VARCHAR(20) NOT NULL DEFAULT 'building',  -- building, ready, deprecated, retired
    scan_status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, passed, failed
    scan_date TIMESTAMPTZ,
    scan_results JSONB,  -- Full scan results
    vulnerability_count JSONB DEFAULT '{"critical": 0, "high": 0, "medium": 0, "low": 0}',
    customer_accounts JSONB DEFAULT '[]',  -- Array of account IDs this image is shared with
    parent_image_version VARCHAR(100),  -- For tracking image lineage/updates
    is_latest BOOLEAN DEFAULT false,  -- Latest version per OS+cloud combination
    release_notes TEXT,
    changelog TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(os_type, os_version, cloud_provider, region, version)
);

-- Indexes
CREATE INDEX idx_hardened_images_os_cloud ON hardened_images(os_type, os_version, cloud_provider);
CREATE INDEX idx_hardened_images_scan_status ON hardened_images(scan_status) WHERE scan_status = 'passed';
CREATE INDEX idx_hardened_images_status ON hardened_images(status);
CREATE INDEX idx_hardened_images_latest ON hardened_images(os_type, os_version, cloud_provider, is_latest) WHERE is_latest = true;
CREATE INDEX idx_hardened_images_agent_version ON hardened_images(agent_version);

-- Image version history for tracking lineage
CREATE TABLE IF NOT EXISTS image_version_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id UUID NOT NULL REFERENCES hardened_images(id) ON DELETE CASCADE,
    parent_image_id UUID REFERENCES hardened_images(id) ON DELETE SET NULL,
    version_from VARCHAR(100),
    version_to VARCHAR(100),
    change_type VARCHAR(50),  -- update, security_patch, rebuild
    change_description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_image_version_history_image ON image_version_history(image_id);
CREATE INDEX idx_image_version_history_parent ON image_version_history(parent_image_id);

-- Constraint: Only images with scan_status = 'passed' can be distributed
-- This is enforced at application level, but we add a check constraint
ALTER TABLE hardened_images ADD CONSTRAINT check_scan_status_for_distribution 
    CHECK (
        (status = 'ready' AND scan_status = 'passed') OR 
        (status != 'ready')
    );

