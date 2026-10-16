-- Alter existing agent_versions table to match new schema
-- This migration updates the existing table structure

-- Add missing columns if they don't exist
DO $$ 
BEGIN
    -- Add version column (rename from sentinelgrid_version or add new)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'agent_versions' AND column_name = 'version') THEN
        IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'agent_versions' AND column_name = 'sentinelgrid_version') THEN
            ALTER TABLE agent_versions RENAME COLUMN sentinelgrid_version TO version;
        ELSE
            ALTER TABLE agent_versions ADD COLUMN version VARCHAR(50);
            -- Populate from existing data if possible
            UPDATE agent_versions SET version = '1.0.0' WHERE version IS NULL;
            ALTER TABLE agent_versions ALTER COLUMN version SET NOT NULL;
            ALTER TABLE agent_versions ADD CONSTRAINT agent_versions_version_unique UNIQUE (version);
        END IF;
    END IF;

    -- Add os_compatibility if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'agent_versions' AND column_name = 'os_compatibility') THEN
        ALTER TABLE agent_versions ADD COLUMN os_compatibility JSONB NOT NULL DEFAULT '[]';
    END IF;

    -- Add status if missing (map from is_deprecated)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'agent_versions' AND column_name = 'status') THEN
        ALTER TABLE agent_versions ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'stable';
        -- Set status based on is_deprecated
        UPDATE agent_versions SET status = 'deprecated' WHERE is_deprecated = true;
    END IF;

    -- Add release_notes if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'agent_versions' AND column_name = 'release_notes') THEN
        ALTER TABLE agent_versions ADD COLUMN release_notes TEXT;
    END IF;

    -- Add is_security_update if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'agent_versions' AND column_name = 'is_security_update') THEN
        ALTER TABLE agent_versions ADD COLUMN is_security_update BOOLEAN DEFAULT false;
    END IF;

    -- Rename end_of_life_date if it exists as deprecation_date
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'agent_versions' AND column_name = 'deprecation_date') THEN
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'agent_versions' AND column_name = 'end_of_life_date') THEN
            ALTER TABLE agent_versions RENAME COLUMN deprecation_date TO end_of_life_date;
        END IF;
    END IF;
END $$;

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_agent_versions_type_latest ON agent_versions(agent_type, is_latest) WHERE is_latest = true;
CREATE INDEX IF NOT EXISTS idx_agent_versions_status ON agent_versions(status);
CREATE INDEX IF NOT EXISTS idx_agent_versions_upstream ON agent_versions(upstream_tool, upstream_version);

-- Create version_compatibility table
CREATE TABLE IF NOT EXISTS version_compatibility (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_version VARCHAR(50) NOT NULL,
    image_version VARCHAR(50) NOT NULL,
    compatibility_status VARCHAR(20) NOT NULL DEFAULT 'untested',
    tested_date TIMESTAMPTZ,
    test_results JSONB,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(agent_version, image_version)
);

-- Add foreign key if version column exists in agent_versions
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'agent_versions' AND column_name = 'version') THEN
        -- Drop existing constraint if any
        ALTER TABLE version_compatibility DROP CONSTRAINT IF EXISTS version_compatibility_agent_version_fkey;
        -- Add foreign key
        ALTER TABLE version_compatibility 
        ADD CONSTRAINT version_compatibility_agent_version_fkey 
        FOREIGN KEY (agent_version) REFERENCES agent_versions(version) ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_version_compatibility_agent ON version_compatibility(agent_version);
CREATE INDEX IF NOT EXISTS idx_version_compatibility_image ON version_compatibility(image_version);
CREATE INDEX IF NOT EXISTS idx_version_compatibility_status ON version_compatibility(compatibility_status);

