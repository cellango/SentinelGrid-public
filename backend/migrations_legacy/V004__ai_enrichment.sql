-- Migration 004: AI Enrichment for Tickets
-- Date: 2025-01-28
-- Description: Create table for AI enrichment results and tracking

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- AI Enrichment table
CREATE TABLE IF NOT EXISTS ticket_ai_enrichments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Enrichment Type
    enrichment_type TEXT NOT NULL,  -- iam, vulnerability, cmdb, network, all
    status TEXT NOT NULL,  -- pending, processing, completed, failed
    
    -- Enrichment Results
    iam_enrichment JSONB,  -- User details, supervisor, permissions, groups
    vulnerability_enrichment JSONB,  -- CVE details, fixes, patches
    cmdb_enrichment JSONB,  -- Asset details, inventory, software
    network_enrichment JSONB,  -- Network connections, IPs, domains
    framework_enrichment JSONB,  -- NIST/MITRE mappings
    
    -- AI Metadata
    model_name TEXT,
    model_version TEXT,
    confidence_score NUMERIC(5, 2),  -- 0-100
    reasoning TEXT,  -- AI reasoning for enrichment
    
    -- Timestamps
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_enrichments_ticket ON ticket_ai_enrichments(ticket_id);
CREATE INDEX IF NOT EXISTS idx_enrichments_tenant ON ticket_ai_enrichments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_enrichments_status ON ticket_ai_enrichments(status);
CREATE INDEX IF NOT EXISTS idx_enrichments_type ON ticket_ai_enrichments(enrichment_type);

-- Comments for documentation
COMMENT ON TABLE ticket_ai_enrichments IS 'AI enrichment results for tickets across IAM, vulnerability, CMDB, network, and framework domains';
COMMENT ON COLUMN ticket_ai_enrichments.iam_enrichment IS 'IAM tab data: users, supervisors, groups, permissions, access history';
COMMENT ON COLUMN ticket_ai_enrichments.vulnerability_enrichment IS 'Vulnerability tab data: CVEs, exploit details, remediation steps, patches';
COMMENT ON COLUMN ticket_ai_enrichments.cmdb_enrichment IS 'CMDB tab data: assets, hardware/software inventory, network info';
COMMENT ON COLUMN ticket_ai_enrichments.network_enrichment IS 'Network tab data: IPs, domains, connections, firewall rules';
COMMENT ON COLUMN ticket_ai_enrichments.framework_enrichment IS 'Framework mappings: NIST controls, MITRE tactics/techniques';

