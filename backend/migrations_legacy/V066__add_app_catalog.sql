-- Migration: Add App Catalog Table
-- Description: Stores prebuilt app templates for one-click SSO setup
-- Date: 2025-01-28

CREATE TABLE IF NOT EXISTS app_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    app_type VARCHAR(50) NOT NULL, -- 'SaaS', 'Internal', 'VPN', 'RADIUS'
    protocol VARCHAR(50) NOT NULL, -- 'SAML', 'OIDC', 'OAuth2', 'RADIUS'
    icon_url VARCHAR(500),
    category VARCHAR(100), -- 'Productivity', 'Development', 'Security', etc.
    is_prebuilt BOOLEAN DEFAULT true,
    setup_guide TEXT, -- Markdown content
    required_fields JSONB, -- Array of required field names
    optional_fields JSONB, -- Array of optional field names
    default_config JSONB, -- Default configuration values
    metadata JSONB, -- Additional metadata
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_app_catalog_name ON app_catalog(name);
CREATE INDEX IF NOT EXISTS idx_app_catalog_category ON app_catalog(category);
CREATE INDEX IF NOT EXISTS idx_app_catalog_active ON app_catalog(is_active);

-- Insert prebuilt app templates
INSERT INTO app_catalog (name, display_name, description, app_type, protocol, category, required_fields, optional_fields, default_config, setup_guide) VALUES
('microsoft_365', 'Microsoft 365', 'Connect Microsoft 365 for SSO with Azure AD', 'SaaS', 'SAML', 'Productivity', 
 '"[\"redirect_uri\", \"entity_id\"]"'::jsonb,
 '"[\"name_id_format\", \"sign_assertions\"]"'::jsonb,
 '{"nameIdFormat": "email"}'::jsonb,
 '## Microsoft 365 SAML Setup\n\n1. Go to Azure AD > Enterprise Applications\n2. Create new application\n3. Configure SAML settings\n4. Copy ACS URL and Entity ID\n5. Enter in SentinelGrid'
),
('google_workspace', 'Google Workspace', 'Connect Google Workspace for SSO', 'SaaS', 'SAML', 'Productivity',
 '"[\"redirect_uri\", \"entity_id\"]"'::jsonb,
 '"[\"name_id_format\"]"'::jsonb,
 '{"nameIdFormat": "email"}'::jsonb,
 '## Google Workspace SAML Setup\n\n1. Go to Admin Console > Apps > SAML apps\n2. Add custom SAML app\n3. Configure SSO URL and Entity ID\n4. Enter in SentinelGrid'
),
('slack', 'Slack', 'Connect Slack workspace for SSO', 'SaaS', 'SAML', 'Communication',
 '"[\"redirect_uri\"]"'::jsonb,
 '"[\"entity_id\", \"sign_assertions\"]"'::jsonb,
 '{}'::jsonb,
 '## Slack SAML Setup\n\n1. Go to Workspace Settings > Authentication\n2. Configure SAML SSO\n3. Copy SSO URL\n4. Enter in SentinelGrid'
),
('zoom', 'Zoom', 'Connect Zoom for SSO', 'SaaS', 'SAML', 'Communication',
 '"[\"redirect_uri\", \"entity_id\"]"'::jsonb,
 '"[\"name_id_format\"]"'::jsonb,
 '{}'::jsonb,
 '## Zoom SAML Setup\n\n1. Go to Advanced > Single Sign-On\n2. Configure SAML\n3. Copy SSO URL and Entity ID\n4. Enter in SentinelGrid'
),
('github', 'GitHub', 'Connect GitHub organization for SSO', 'SaaS', 'SAML', 'Development',
 '"[\"redirect_uri\"]"'::jsonb,
 '"[\"entity_id\", \"sign_assertions\"]"'::jsonb,
 '{}'::jsonb,
 '## GitHub SAML Setup\n\n1. Go to Organization Settings > Security\n2. Enable SAML SSO\n3. Copy SSO URL\n4. Enter in SentinelGrid'
),
('gitlab', 'GitLab', 'Connect GitLab for SSO', 'SaaS', 'SAML', 'Development',
 '"[\"redirect_uri\", \"entity_id\"]"'::jsonb,
 '"[\"name_id_format\"]"'::jsonb,
 '{}'::jsonb,
 '## GitLab SAML Setup\n\n1. Go to Settings > General > Sign-in restrictions\n2. Configure SAML\n3. Copy SSO URL and Entity ID\n4. Enter in SentinelGrid'
),
('salesforce', 'Salesforce', 'Connect Salesforce for SSO', 'SaaS', 'SAML', 'CRM',
 '"[\"redirect_uri\", \"entity_id\"]"'::jsonb,
 '"[\"name_id_format\", \"sign_assertions\"]"'::jsonb,
 '{"nameIdFormat": "email"}'::jsonb,
 '## Salesforce SAML Setup\n\n1. Go to Setup > Single Sign-On Settings\n2. Create new SAML configuration\n3. Copy Login URL and Entity ID\n4. Enter in SentinelGrid'
),
('quickbooks', 'QuickBooks', 'Connect QuickBooks for SSO', 'SaaS', 'SAML', 'Finance',
 '"[\"redirect_uri\", \"entity_id\"]"'::jsonb,
 '"[\"name_id_format\"]"'::jsonb,
 '{}'::jsonb,
 '## QuickBooks SAML Setup\n\n1. Go to Company Settings > Security\n2. Configure SAML SSO\n3. Copy SSO URL and Entity ID\n4. Enter in SentinelGrid'
),
('dropbox', 'Dropbox', 'Connect Dropbox for SSO', 'SaaS', 'SAML', 'Storage',
 '"[\"redirect_uri\"]"'::jsonb,
 '"[\"entity_id\", \"sign_assertions\"]"'::jsonb,
 '{}'::jsonb,
 '## Dropbox SAML Setup\n\n1. Go to Admin Console > Authentication\n2. Configure SAML SSO\n3. Copy SSO URL\n4. Enter in SentinelGrid'
)
ON CONFLICT (name) DO NOTHING;

-- Create table for connected apps (tenant-specific)
CREATE TABLE IF NOT EXISTS connected_apps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    catalog_app_id UUID REFERENCES app_catalog(id),
    client_id VARCHAR(255) NOT NULL, -- Keycloak client ID
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    protocol VARCHAR(50) NOT NULL,
    config JSONB NOT NULL, -- App-specific configuration
    is_active BOOLEAN DEFAULT true,
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    connected_by UUID, -- User ID who connected it
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, client_id)
);

-- Create indexes for connected apps
CREATE INDEX IF NOT EXISTS idx_connected_apps_tenant ON connected_apps(tenant_id);
CREATE INDEX IF NOT EXISTS idx_connected_apps_catalog ON connected_apps(catalog_app_id);
CREATE INDEX IF NOT EXISTS idx_connected_apps_active ON connected_apps(is_active);

-- Add comment
COMMENT ON TABLE app_catalog IS 'Prebuilt app templates for SSO setup';
COMMENT ON TABLE connected_apps IS 'Apps connected by tenants';
