-- Agent Versions Management Schema
-- Tracks rebranded agent versions and their availability

CREATE TABLE IF NOT EXISTS agent_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version VARCHAR(50) NOT NULL UNIQUE,  -- Semantic version: MAJOR.MINOR.PATCH
    agent_type VARCHAR(50) NOT NULL,  -- endpoint, cloud, network
    upstream_tool VARCHAR(50) NOT NULL,  -- wazuh, suricata, etc.
    upstream_version VARCHAR(50) NOT NULL,  -- 4.8.0
    os_compatibility JSONB NOT NULL DEFAULT '[]',  -- ["amazon-linux-2", "ubuntu-22.04", ...]
    package_urls JSONB NOT NULL DEFAULT '{}',  -- {"rpm": "...", "deb": "...", "msi": "...", "pkg": "..."}
    checksums JSONB NOT NULL DEFAULT '{}',  -- SHA256 checksums per package
    release_date DATE NOT NULL DEFAULT CURRENT_DATE,
    end_of_life_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'stable',  -- stable, beta, deprecated
    changelog TEXT,
    release_notes TEXT,
    is_latest BOOLEAN DEFAULT false,
    is_security_update BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_agent_versions_type_latest ON agent_versions(agent_type, is_latest) WHERE is_latest = true;
CREATE INDEX idx_agent_versions_status ON agent_versions(status);
CREATE INDEX idx_agent_versions_upstream ON agent_versions(upstream_tool, upstream_version);

-- Version compatibility tracking
CREATE TABLE IF NOT EXISTS version_compatibility (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_version VARCHAR(50) NOT NULL REFERENCES agent_versions(version) ON DELETE CASCADE,
    image_version VARCHAR(50) NOT NULL,  -- References hardened_images.version
    compatibility_status VARCHAR(20) NOT NULL DEFAULT 'untested',  -- compatible, incompatible, untested
    tested_date TIMESTAMPTZ,
    test_results JSONB,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(agent_version, image_version)
);

CREATE INDEX idx_version_compatibility_agent ON version_compatibility(agent_version);
CREATE INDEX idx_version_compatibility_image ON version_compatibility(image_version);
CREATE INDEX idx_version_compatibility_status ON version_compatibility(compatibility_status);

