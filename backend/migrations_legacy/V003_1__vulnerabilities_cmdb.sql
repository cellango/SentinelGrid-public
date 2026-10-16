-- Migration 003: Vulnerabilities and CMDB Assets
-- Date: 2025-01-28
-- Description: Create tables for vulnerability management (CVE) and CMDB asset inventory

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Vulnerabilities table (CVE data)
CREATE TABLE IF NOT EXISTS vulnerabilities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- CVE Information
    cve_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    cvss_score NUMERIC(5, 2),
    cvss_severity TEXT,  -- CRITICAL, HIGH, MEDIUM, LOW
    cvss_vector TEXT,  -- CVSS vector string
    
    -- Vulnerability Details
    affected_products JSONB,  -- [{"vendor": "...", "product": "...", "version": "..."}]
    exploit_available BOOLEAN DEFAULT false,
    exploit_maturity TEXT,  -- POC, WEAPONIZED, etc.
    patch_available BOOLEAN DEFAULT false,
    
    -- Remediation
    remediation_steps JSONB,  -- Array of remediation steps
    patches JSONB,  -- [{"vendor": "...", "patch_id": "...", "url": "..."}]
    workarounds JSONB,  -- Array of workarounds
    
    -- Framework Associations
    nist_controls JSONB,  -- NIST controls related to this vulnerability
    mitre_techniques JSONB,  -- MITRE techniques that exploit this vulnerability
    
    -- Metadata
    published_date TIMESTAMPTZ,
    last_modified_date TIMESTAMPTZ,
    source TEXT DEFAULT 'nvd',  -- nvd, mitre, custom
    raw_data JSONB,  -- Full CVE JSON from NVD
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Unique constraint on cve_id per tenant (same CVE can exist for multiple tenants)
    CONSTRAINT unique_cve_per_tenant UNIQUE (tenant_id, cve_id)
);

-- CMDB Assets table
CREATE TABLE IF NOT EXISTS assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Asset Identification
    asset_id TEXT NOT NULL,  -- Unique asset identifier
    asset_type TEXT NOT NULL,  -- server, workstation, network_device, cloud_instance
    name TEXT NOT NULL,
    hostname TEXT,
    ip_address TEXT,
    mac_address TEXT,
    
    -- Hardware Information
    manufacturer TEXT,
    model TEXT,
    serial_number TEXT,
    hardware_specs JSONB,  -- CPU, RAM, storage, etc.
    
    -- Software Information
    operating_system TEXT,
    os_version TEXT,
    installed_software JSONB,  -- [{"name": "...", "version": "...", "vendor": "..."}]
    installed_patches JSONB,  -- Array of patch IDs
    
    -- Network Information
    network_segment TEXT,
    vlan TEXT,
    firewall_rules JSONB,  -- Associated firewall rules
    
    -- Ownership & Location
    owner TEXT,  -- User/team owner
    location TEXT,
    department TEXT,
    
    -- Security Information
    vulnerabilities JSONB,  -- Array of CVE IDs affecting this asset
    compliance_status TEXT,  -- compliant, non_compliant, unknown
    last_scan_date TIMESTAMPTZ,
    
    -- Metadata
    source TEXT,  -- cmdb, cloud_query, manual
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Unique constraint on asset_id per tenant
    CONSTRAINT unique_asset_per_tenant UNIQUE (tenant_id, asset_id)
);

-- Tickets table (Enhanced ticket/incident management)
CREATE TABLE IF NOT EXISTS tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    external_id TEXT,  -- ID in external system (Jira, ServiceNow, TheHive)
    source TEXT NOT NULL DEFAULT 'thehive',  -- thehive, jira, servicenow
    
    -- Overview (Main Page)
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL,  -- open, in_progress, resolved, closed
    severity TEXT,  -- critical, high, medium, low
    priority TEXT,  -- P1, P2, P3, P4
    category TEXT,  -- malware, phishing, suspicious_login, etc.
    
    -- Framework Associations
    nist_controls JSONB,  -- Array of NIST control mappings
    mitre_tactics JSONB,  -- Array of MITRE tactic mappings
    mitre_techniques JSONB,  -- Array of MITRE technique mappings
    
    -- Vulnerability Association
    cve_ids TEXT[],  -- Array of CVE IDs
    exploit_indicators JSONB,  -- Indicators of exploitation
    
    -- Tab Data (Stored as JSON for flexibility)
    iam_data JSONB,  -- IAM tab data (users, supervisors, permissions)
    vm_data JSONB,  -- Vulnerability Management tab data (CVEs, fixes)
    cmdb_data JSONB,  -- CMDB tab data (assets, inventory)
    network_data JSONB,  -- Network tab data (IPs, domains, connections)
    timeline_data JSONB,  -- Timeline tab data (events, actions)
    
    -- AI Enrichment
    ai_enrichment_status TEXT DEFAULT 'pending',  -- pending, enriching, completed, failed
    ai_enrichment_summary TEXT,  -- AI-generated summary
    ai_enrichment_timestamp TIMESTAMPTZ,
    
    -- Metadata
    assigned_to TEXT,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Ticket-Alert linking table
CREATE TABLE IF NOT EXISTS ticket_alerts (
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    alert_id UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    PRIMARY KEY (ticket_id, alert_id)
);

-- Ticket-Vulnerability linking table
CREATE TABLE IF NOT EXISTS ticket_vulnerabilities (
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    vulnerability_id UUID NOT NULL REFERENCES vulnerabilities(id) ON DELETE CASCADE,
    PRIMARY KEY (ticket_id, vulnerability_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_tenant ON vulnerabilities(tenant_id);
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_cve ON vulnerabilities(cve_id);
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_severity ON vulnerabilities(cvss_severity);
CREATE INDEX IF NOT EXISTS idx_vulnerabilities_exploit ON vulnerabilities(exploit_available);

CREATE INDEX IF NOT EXISTS idx_assets_tenant ON assets(tenant_id);
CREATE INDEX IF NOT EXISTS idx_assets_asset_id ON assets(asset_id);
CREATE INDEX IF NOT EXISTS idx_assets_hostname ON assets(hostname);
CREATE INDEX IF NOT EXISTS idx_assets_ip ON assets(ip_address);
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);

CREATE INDEX IF NOT EXISTS idx_tickets_tenant ON tickets(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_severity ON tickets(severity);
CREATE INDEX IF NOT EXISTS idx_tickets_external_id ON tickets(external_id);
CREATE INDEX IF NOT EXISTS idx_tickets_nist_controls ON tickets USING GIN (nist_controls);
CREATE INDEX IF NOT EXISTS idx_tickets_mitre_tactics ON tickets USING GIN (mitre_tactics);
CREATE INDEX IF NOT EXISTS idx_tickets_mitre_techniques ON tickets USING GIN (mitre_techniques);
CREATE INDEX IF NOT EXISTS idx_tickets_cve_ids ON tickets USING GIN (cve_ids);

-- Comments for documentation
COMMENT ON TABLE vulnerabilities IS 'CVE vulnerability database with exploit details and remediation';
COMMENT ON TABLE assets IS 'CMDB asset inventory (hardware, software, network)';
COMMENT ON TABLE tickets IS 'Enhanced ticket/incident management with tab-based data structure';
COMMENT ON TABLE ticket_alerts IS 'Many-to-many relationship between tickets and alerts';
COMMENT ON TABLE ticket_vulnerabilities IS 'Many-to-many relationship between tickets and vulnerabilities';

