-- Migration: Onboarding and Multi-Cloud Support Tables
-- Created: 2025-11-30
-- Description: Creates tables for customer onboarding, multi-cloud integration, endpoint agents, hardened images, and Git security

-- ============================================================================
-- Identity Provider Configuration
-- ============================================================================
CREATE TABLE IF NOT EXISTS customer_idp_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    idp_type VARCHAR(50) NOT NULL, -- google, microsoft, okta, keycloak, none
    config_json JSONB NOT NULL, -- Encrypted tokens/secrets (encrypted at application level)
    status VARCHAR(50) DEFAULT 'pending', -- pending, connected, error, disconnected
    connected_at TIMESTAMPTZ,
    last_sync_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(customer_id, idp_type)
);

CREATE INDEX idx_customer_idp_config_customer_id ON customer_idp_config(customer_id);
CREATE INDEX idx_customer_idp_config_status ON customer_idp_config(status);

COMMENT ON TABLE customer_idp_config IS 'Stores identity provider connection configurations for customers';
COMMENT ON COLUMN customer_idp_config.config_json IS 'Encrypted JSON containing OAuth tokens, client IDs/secrets, etc.';

-- ============================================================================
-- Multi-Cloud Account Configuration
-- ============================================================================
CREATE TABLE IF NOT EXISTS customer_cloud_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    cloud_provider VARCHAR(50) NOT NULL, -- aws, azure, gcp
    account_id VARCHAR(255) NOT NULL, -- AWS Account ID, Azure Subscription ID, GCP Project ID
    account_name VARCHAR(255), -- Friendly name for the account
    integration_method VARCHAR(50), -- terraform, cloudformation, arm_template, deployment_manager, manual
    monitor_role_arn VARCHAR(512), -- IAM Role ARN for AWS
    external_id VARCHAR(255), -- External ID for AWS cross-account trust
    service_principal_id VARCHAR(255), -- Service Principal ID for Azure/GCP
    service_principal_secret_encrypted TEXT, -- Encrypted secret for Azure/GCP (if needed)
    status VARCHAR(50) DEFAULT 'pending', -- pending, connected, error, disconnected
    connected_at TIMESTAMPTZ,
    last_sync_at TIMESTAMPTZ,
    last_scan_at TIMESTAMPTZ, -- Last posture scan time
    error_message TEXT,
    metadata JSONB, -- Additional provider-specific metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(customer_id, cloud_provider, account_id)
);

CREATE INDEX idx_customer_cloud_accounts_customer_id ON customer_cloud_accounts(customer_id);
CREATE INDEX idx_customer_cloud_accounts_provider ON customer_cloud_accounts(cloud_provider);
CREATE INDEX idx_customer_cloud_accounts_status ON customer_cloud_accounts(status);

COMMENT ON TABLE customer_cloud_accounts IS 'Stores multi-cloud account connections (AWS, Azure, GCP)';
COMMENT ON COLUMN customer_cloud_accounts.monitor_role_arn IS 'AWS IAM Role ARN for cross-account access';
COMMENT ON COLUMN customer_cloud_accounts.external_id IS 'External ID for AWS cross-account role assumption';

-- ============================================================================
-- Endpoint Agent Registration
-- ============================================================================
CREATE TABLE IF NOT EXISTS customer_endpoint_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    agent_id VARCHAR(255) NOT NULL, -- Wazuh agent ID or other agent identifier
    agent_type VARCHAR(50) NOT NULL, -- endpoint_protection, cloud_agent, network_sensor
    hostname VARCHAR(255),
    ip_address INET,
    os_type VARCHAR(50), -- linux, windows, macos
    os_version VARCHAR(100), -- Ubuntu 22.04, Windows Server 2022, etc.
    os_arch VARCHAR(50), -- x86_64, arm64, etc.
    agent_version VARCHAR(50), -- SentinelGrid agent version
    registration_token VARCHAR(255), -- Encrypted registration token
    status VARCHAR(50) DEFAULT 'pending', -- pending, active, disconnected, error
    registered_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    metadata JSONB, -- Additional agent metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(customer_id, agent_id)
);

CREATE INDEX idx_customer_endpoint_agents_customer_id ON customer_endpoint_agents(customer_id);
CREATE INDEX idx_customer_endpoint_agents_status ON customer_endpoint_agents(status);
CREATE INDEX idx_customer_endpoint_agents_last_seen ON customer_endpoint_agents(last_seen_at);

COMMENT ON TABLE customer_endpoint_agents IS 'Tracks registered endpoint protection agents';
COMMENT ON COLUMN customer_endpoint_agents.agent_id IS 'Unique agent identifier from Wazuh or other agent system';

-- ============================================================================
-- Onboarding Progress Tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS onboarding_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    step_idp_completed BOOLEAN DEFAULT FALSE,
    step_idp_completed_at TIMESTAMPTZ,
    step_cloud_completed BOOLEAN DEFAULT FALSE,
    step_cloud_completed_at TIMESTAMPTZ,
    step_endpoint_completed BOOLEAN DEFAULT FALSE,
    step_endpoint_completed_at TIMESTAMPTZ,
    step_git_completed BOOLEAN DEFAULT FALSE,
    step_git_completed_at TIMESTAMPTZ,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    onboarding_completed_at TIMESTAMPTZ,
    last_accessed_step INTEGER DEFAULT 1, -- 1=IdP, 2=Cloud, 3=Endpoint, 4=Git
    dismissed_banner BOOLEAN DEFAULT FALSE, -- User dismissed setup banner
    dismissed_banner_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(customer_id)
);

CREATE INDEX idx_onboarding_progress_customer_id ON onboarding_progress(customer_id);
CREATE INDEX idx_onboarding_progress_completed ON onboarding_progress(onboarding_completed);

COMMENT ON TABLE onboarding_progress IS 'Tracks customer onboarding wizard progress';

-- ============================================================================
-- Hardened Image Registry
-- ============================================================================
CREATE TABLE IF NOT EXISTS hardened_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    os_flavor VARCHAR(50) NOT NULL, -- amazon-linux-2, ubuntu-22.04, rhel-8, debian-12, windows-server-2022
    os_version VARCHAR(50), -- 22.04, 8, 12, 2022, etc.
    cis_level INTEGER NOT NULL, -- 1 or 2
    cloud_provider VARCHAR(50) NOT NULL, -- aws, azure, gcp
    region VARCHAR(50) NOT NULL, -- us-east-1, westus, us-central1, etc.
    image_id VARCHAR(255) NOT NULL, -- AMI ID, image URI, etc.
    image_name VARCHAR(255),
    build_date DATE NOT NULL,
    agent_version VARCHAR(50), -- SentinelGrid agent version baked in
    checksum VARCHAR(255), -- SHA256 checksum
    download_url TEXT, -- Public download URL if applicable
    is_public BOOLEAN DEFAULT true,
    is_latest BOOLEAN DEFAULT false, -- Latest version for this OS/CIS level/region
    metadata JSONB, -- Additional image metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_hardened_images_os_flavor ON hardened_images(os_flavor);
CREATE INDEX idx_hardened_images_cloud_provider ON hardened_images(cloud_provider);
CREATE INDEX idx_hardened_images_region ON hardened_images(region);
CREATE INDEX idx_hardened_images_latest ON hardened_images(os_flavor, cis_level, cloud_provider, region, is_latest) WHERE is_latest = true;

COMMENT ON TABLE hardened_images IS 'Registry of CIS-hardened OS images available to customers';
COMMENT ON COLUMN hardened_images.is_latest IS 'True for the most recent build of this OS/CIS level/region combination';

-- ============================================================================
-- Git Provider Configuration
-- ============================================================================
CREATE TABLE IF NOT EXISTS customer_git_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL, -- github, gitlab, bitbucket, azure_devops, self_hosted
    provider_type VARCHAR(50), -- cloud, enterprise, self_hosted
    organization_name VARCHAR(255), -- GitHub org, GitLab group, etc.
    access_token_encrypted TEXT, -- Encrypted OAuth token or API key
    webhook_url TEXT, -- Webhook URL for self-hosted or custom integrations
    webhook_secret_encrypted TEXT, -- Encrypted webhook secret
    status VARCHAR(50) DEFAULT 'pending', -- pending, connected, error, disconnected
    connected_at TIMESTAMPTZ,
    last_sync_at TIMESTAMPTZ,
    error_message TEXT,
    metadata JSONB, -- Provider-specific configuration
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(customer_id, provider, organization_name)
);

CREATE INDEX idx_customer_git_providers_customer_id ON customer_git_providers(customer_id);
CREATE INDEX idx_customer_git_providers_status ON customer_git_providers(status);

COMMENT ON TABLE customer_git_providers IS 'Stores Git provider connection configurations';

-- ============================================================================
-- Git Repository Inventory
-- ============================================================================
CREATE TABLE IF NOT EXISTS git_repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    git_provider_id UUID REFERENCES customer_git_providers(id) ON DELETE CASCADE,
    repo_name VARCHAR(255) NOT NULL,
    repo_url TEXT NOT NULL,
    repo_id VARCHAR(255), -- Provider-specific repository ID
    is_public BOOLEAN DEFAULT false,
    default_branch VARCHAR(100),
    branch_protection_enabled BOOLEAN DEFAULT false,
    code_review_required BOOLEAN DEFAULT false,
    last_scan_at TIMESTAMPTZ,
    scan_status VARCHAR(50), -- pending, scanning, completed, error
    metadata JSONB, -- Repository metadata from provider
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(customer_id, git_provider_id, repo_name)
);

CREATE INDEX idx_git_repositories_customer_id ON git_repositories(customer_id);
CREATE INDEX idx_git_repositories_git_provider_id ON git_repositories(git_provider_id);
CREATE INDEX idx_git_repositories_scan_status ON git_repositories(scan_status);

COMMENT ON TABLE git_repositories IS 'Inventory of customer Git repositories';

-- ============================================================================
-- Git Security Findings
-- ============================================================================
CREATE TABLE IF NOT EXISTS git_security_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    repo_id UUID REFERENCES git_repositories(id) ON DELETE CASCADE,
    finding_type VARCHAR(50) NOT NULL, -- secret, vulnerability, code_issue, dependency_vulnerability
    severity VARCHAR(50) NOT NULL, -- critical, high, medium, low, info
    title TEXT NOT NULL,
    description TEXT,
    file_path TEXT,
    line_number INTEGER,
    commit_sha VARCHAR(40),
    commit_message TEXT,
    author_email VARCHAR(255),
    scanner_tool VARCHAR(50), -- gitleaks, trivy, semgrep, snyk, etc.
    scanner_rule_id VARCHAR(255), -- Rule ID from scanner
    status VARCHAR(50) DEFAULT 'open', -- open, resolved, false_positive, ignored
    resolved_at TIMESTAMPTZ,
    resolved_by UUID, -- User ID who resolved it
    remediation_notes TEXT,
    detected_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_git_security_findings_customer_id ON git_security_findings(customer_id);
CREATE INDEX idx_git_security_findings_repo_id ON git_security_findings(repo_id);
CREATE INDEX idx_git_security_findings_type ON git_security_findings(finding_type);
CREATE INDEX idx_git_security_findings_severity ON git_security_findings(severity);
CREATE INDEX idx_git_security_findings_status ON git_security_findings(status);
CREATE INDEX idx_git_security_findings_detected_at ON git_security_findings(detected_at);

COMMENT ON TABLE git_security_findings IS 'Security findings from Git repository scanning';

-- ============================================================================
-- Agent Version Management
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type VARCHAR(50) NOT NULL, -- endpoint_protection, cloud_agent, network_sensor
    upstream_tool VARCHAR(50) NOT NULL, -- wazuh, suricata, custom
    upstream_version VARCHAR(50) NOT NULL, -- 4.8.0, 7.0.0, etc.
    sentinelgrid_version VARCHAR(50) NOT NULL, -- 1.0.0, 1.1.0, etc.
    release_date DATE NOT NULL,
    download_urls JSONB NOT NULL, -- Platform-specific download URLs
    checksums JSONB NOT NULL, -- SHA256 checksums per platform
    changelog TEXT,
    is_latest BOOLEAN DEFAULT false,
    is_deprecated BOOLEAN DEFAULT false,
    deprecation_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_versions_agent_type ON agent_versions(agent_type);
CREATE INDEX idx_agent_versions_latest ON agent_versions(agent_type, is_latest) WHERE is_latest = true;
CREATE INDEX idx_agent_versions_upstream ON agent_versions(upstream_tool, upstream_version);

COMMENT ON TABLE agent_versions IS 'Manages agent version information and download URLs';
COMMENT ON COLUMN agent_versions.download_urls IS 'JSON object with platform keys (linux_rpm, linux_deb, windows, macos) and URL values';
COMMENT ON COLUMN agent_versions.checksums IS 'JSON object with platform keys and SHA256 checksum values';

-- ============================================================================
-- Update triggers for updated_at columns
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to all tables with updated_at
CREATE TRIGGER update_customer_idp_config_updated_at BEFORE UPDATE ON customer_idp_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_customer_cloud_accounts_updated_at BEFORE UPDATE ON customer_cloud_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_customer_endpoint_agents_updated_at BEFORE UPDATE ON customer_endpoint_agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_onboarding_progress_updated_at BEFORE UPDATE ON onboarding_progress
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_hardened_images_updated_at BEFORE UPDATE ON hardened_images
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_customer_git_providers_updated_at BEFORE UPDATE ON customer_git_providers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_git_repositories_updated_at BEFORE UPDATE ON git_repositories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_git_security_findings_updated_at BEFORE UPDATE ON git_security_findings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_versions_updated_at BEFORE UPDATE ON agent_versions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Initial data: Create onboarding_progress for existing customers
-- ============================================================================
INSERT INTO onboarding_progress (customer_id, onboarding_completed)
SELECT id, true
FROM customers
WHERE id NOT IN (SELECT customer_id FROM onboarding_progress)
ON CONFLICT (customer_id) DO NOTHING;

