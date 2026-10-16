-- Migration 037: AI Provider Credentials Management
-- Purpose: Store configuration for how gateway accesses customer-controlled provider API keys
-- Created: 2025-12-03

-- =====================================================
-- TABLE: ai_provider_credentials
-- =====================================================
-- Stores configuration for accessing customer's AI provider keys
-- Keys themselves are NEVER stored here - only references to customer's vaults

CREATE TABLE IF NOT EXISTS ai_provider_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL,
    provider VARCHAR(50) NOT NULL, -- 'openai', 'anthropic', 'azure-openai'
    deployment_model VARCHAR(20) NOT NULL, -- 'self-hosted', 'saas'
    access_method VARCHAR(30) NOT NULL, -- 'vault-delegation', 'customer-proxy', 'dual-key'
    
    -- For vault-delegation (customer grants us read-only IAM role)
    vault_type VARCHAR(20), -- 'aws-secrets', 'azure-keyvault', 'hashicorp-vault'
    vault_secret_path TEXT, -- Path to secret in customer's vault
    iam_role_arn TEXT, -- AWS IAM role ARN or Azure service principal ID
    vault_region VARCHAR(50), -- AWS region or Azure location
    
    -- For customer-proxy (customer runs key-holder sidecar)
    proxy_endpoint_url TEXT, -- URL to customer's proxy service
    proxy_auth_token_hash TEXT, -- Hashed authentication token
    
    -- For dual-key (separate gateway key vs emergency key)
    gateway_key_fingerprint TEXT, -- Hash of first 8 chars of gateway key
    emergency_key_fingerprint TEXT, -- Hash of first 8 chars of emergency key
    emergency_key_last_detected TIMESTAMP, -- When emergency key was last used
    
    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    last_validated TIMESTAMP, -- Last time we successfully fetched a key
    validation_error TEXT, -- Last error if validation failed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),
    
    -- Constraints
    CONSTRAINT valid_deployment_model CHECK (deployment_model IN ('self-hosted', 'saas')),
    CONSTRAINT valid_access_method CHECK (access_method IN ('vault-delegation', 'customer-proxy', 'dual-key')),
    CONSTRAINT valid_vault_type CHECK (vault_type IS NULL OR vault_type IN ('aws-secrets', 'azure-keyvault', 'hashicorp-vault')),
    CONSTRAINT valid_provider CHECK (provider IN ('openai', 'anthropic', 'azure-openai', 'local'))
);

-- Indexes for performance
CREATE INDEX idx_provider_creds_org ON ai_provider_credentials(org_id, provider);
CREATE INDEX idx_provider_creds_active ON ai_provider_credentials(org_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_provider_creds_validation ON ai_provider_credentials(last_validated) WHERE is_active = TRUE;

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_ai_provider_credentials_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_ai_provider_credentials_updated_at
    BEFORE UPDATE ON ai_provider_credentials
    FOR EACH ROW
    EXECUTE FUNCTION update_ai_provider_credentials_updated_at();

-- Comments for documentation
COMMENT ON TABLE ai_provider_credentials IS 'Configuration for accessing customer-controlled AI provider API keys. Keys are NEVER stored here - only references to customer vaults.';
COMMENT ON COLUMN ai_provider_credentials.deployment_model IS 'Whether gateway runs in customer infra (self-hosted) or SentinelGrid infra (saas)';
COMMENT ON COLUMN ai_provider_credentials.access_method IS 'How gateway accesses the key: vault-delegation (cross-account IAM), customer-proxy (customer-hosted sidecar), or dual-key (separate keys)';
COMMENT ON COLUMN ai_provider_credentials.iam_role_arn IS 'AWS IAM role ARN or Azure service principal ID that gateway assumes to read secret';
COMMENT ON COLUMN ai_provider_credentials.gateway_key_fingerprint IS 'First 8 chars SHA-256 hash of gateway key for identification (not security)';
COMMENT ON COLUMN ai_provider_credentials.emergency_key_last_detected IS 'Timestamp when emergency key usage was detected (triggers alert)';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ai_provider_credentials TO sg;

