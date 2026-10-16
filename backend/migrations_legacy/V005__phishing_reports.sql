-- Migration: Add phishing reports and observables tables
-- Date: 2025-01-28
-- Description: Support for Hero Flow 3 - Phishing email triage

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Phishing reports table
CREATE TABLE IF NOT EXISTS phishing_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Email metadata
    message_id TEXT UNIQUE NOT NULL,  -- Email Message-ID header
    subject TEXT,
    from_address TEXT NOT NULL,
    to_address TEXT NOT NULL,  -- phishing@customer.sentinelgrid.com
    reply_to TEXT,
    received_date TIMESTAMPTZ NOT NULL,
    reported_by TEXT,  -- Email address of reporter (from Forwarded-From header)
    
    -- Email content
    raw_email TEXT NOT NULL,  -- Full RFC 822 email
    html_body TEXT,
    text_body TEXT,
    attachments JSONB,  -- Array of attachment metadata
    
    -- Classification
    classification TEXT,  -- 'phishing', 'benign', 'suspicious', 'pending'
    classification_confidence NUMERIC(5,2),  -- 0-100
    classified_by TEXT,  -- 'ai', 'analyst', 'system'
    classified_at TIMESTAMPTZ,
    
    -- AI Analysis
    ai_analysis JSONB,  -- Full AI analysis response
    ai_summary TEXT,
    ai_recommended_actions JSONB,
    mitre_tactics JSONB,  -- e.g., ["TA0001", "TA0004"]
    mitre_techniques JSONB,  -- e.g., ["T1566", "T1566.001"]
    nist_controls JSONB,  -- e.g., ["AT-2", "IR-4", "SI-4"]
    
    -- Status
    status TEXT NOT NULL DEFAULT 'new',  -- 'new', 'in_review', 'confirmed_phishing', 'confirmed_benign', 'resolved'
    severity TEXT,  -- 'critical', 'high', 'medium', 'low'
    assigned_to TEXT,  -- User ID
    
    -- Ticket/Incident linkage
    ticket_id UUID REFERENCES tickets(id),
    incident_id UUID REFERENCES incidents(id),
    
    -- Similar emails
    similar_emails JSONB,  -- Array of similar email IDs found
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Email observables (extracted IOCs)
CREATE TABLE IF NOT EXISTS phishing_observables (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    phishing_report_id UUID NOT NULL REFERENCES phishing_reports(id) ON DELETE CASCADE,
    
    observable_type TEXT NOT NULL,  -- 'ip', 'domain', 'url', 'email', 'hash'
    observable_value TEXT NOT NULL,
    observable_context TEXT,  -- Where it was found (e.g., "From header", "Link in body")
    
    -- Threat intelligence
    threat_intel JSONB,  -- CTI enrichment results
    reputation_score INTEGER,  -- 0-100
    is_malicious BOOLEAN,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Ensure unique observables per report
    UNIQUE(phishing_report_id, observable_type, observable_value)
);

-- Indexes for phishing_reports
CREATE INDEX IF NOT EXISTS idx_phishing_reports_tenant_id ON phishing_reports(tenant_id);
CREATE INDEX IF NOT EXISTS idx_phishing_reports_status ON phishing_reports(status);
CREATE INDEX IF NOT EXISTS idx_phishing_reports_classification ON phishing_reports(classification);
CREATE INDEX IF NOT EXISTS idx_phishing_reports_reported_by ON phishing_reports(reported_by);
CREATE INDEX IF NOT EXISTS idx_phishing_reports_message_id ON phishing_reports(message_id);
CREATE INDEX IF NOT EXISTS idx_phishing_reports_created_at ON phishing_reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_phishing_reports_ticket_id ON phishing_reports(ticket_id);
CREATE INDEX IF NOT EXISTS idx_phishing_reports_incident_id ON phishing_reports(incident_id);

-- GIN indexes for JSONB columns
CREATE INDEX IF NOT EXISTS idx_phishing_reports_mitre_tactics ON phishing_reports USING GIN (mitre_tactics);
CREATE INDEX IF NOT EXISTS idx_phishing_reports_mitre_techniques ON phishing_reports USING GIN (mitre_techniques);
CREATE INDEX IF NOT EXISTS idx_phishing_reports_nist_controls ON phishing_reports USING GIN (nist_controls);
CREATE INDEX IF NOT EXISTS idx_phishing_reports_similar_emails ON phishing_reports USING GIN (similar_emails);

-- Indexes for phishing_observables
CREATE INDEX IF NOT EXISTS idx_phishing_observables_report_id ON phishing_observables(phishing_report_id);
CREATE INDEX IF NOT EXISTS idx_phishing_observables_tenant_id ON phishing_observables(tenant_id);
CREATE INDEX IF NOT EXISTS idx_phishing_observables_type_value ON phishing_observables(observable_type, observable_value);
CREATE INDEX IF NOT EXISTS idx_phishing_observables_is_malicious ON phishing_observables(is_malicious) WHERE is_malicious = true;

-- Add comments for documentation
COMMENT ON TABLE phishing_reports IS 'Phishing email reports submitted by users';
COMMENT ON TABLE phishing_observables IS 'Indicators of compromise extracted from phishing emails';

COMMENT ON COLUMN phishing_reports.message_id IS 'RFC 822 Message-ID header value';
COMMENT ON COLUMN phishing_reports.reported_by IS 'Email address of the user who reported the phishing email';
COMMENT ON COLUMN phishing_reports.raw_email IS 'Full RFC 822 email content';
COMMENT ON COLUMN phishing_reports.classification IS 'AI or analyst classification: phishing, benign, suspicious, or pending';
COMMENT ON COLUMN phishing_reports.ai_analysis IS 'Complete AI analysis response including reasoning and recommendations';

