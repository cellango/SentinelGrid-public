-- Migration: Compliance Control Library
-- Date: 2025-12-02
-- Purpose: SOC 2, NIST CSF, HIPAA, PCI DSS control library and mappings

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Compliance frameworks
CREATE TABLE IF NOT EXISTS compliance_frameworks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    framework_code VARCHAR(50) UNIQUE NOT NULL, -- 'SOC2', 'NIST_CSF', 'HIPAA', 'PCI_DSS', 'CMMC'
    framework_name VARCHAR(255) NOT NULL,
    version VARCHAR(50),
    description TEXT,
    official_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed frameworks
INSERT INTO compliance_frameworks (framework_code, framework_name, version, description) VALUES
('SOC2', 'SOC 2 Trust Services Criteria', '2017', 'AICPA Trust Services Criteria for Security, Availability, Processing Integrity, Confidentiality, and Privacy'),
('NIST_CSF', 'NIST Cybersecurity Framework', '1.1', 'Framework for improving critical infrastructure cybersecurity'),
('HIPAA', 'HIPAA Security Rule', '2013', 'Health Insurance Portability and Accountability Act Security Rule'),
('PCI_DSS', 'PCI DSS', '4.0', 'Payment Card Industry Data Security Standard'),
('CMMC', 'CMMC', '2.0', 'Cybersecurity Maturity Model Certification')
ON CONFLICT (framework_code) DO NOTHING;

-- Compliance controls
CREATE TABLE IF NOT EXISTS compliance_controls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    framework_id UUID NOT NULL REFERENCES compliance_frameworks(id) ON DELETE CASCADE,
    control_id VARCHAR(100) NOT NULL, -- e.g., 'CC6.1', 'IA-2', '164.312(a)(2)(i)', 'AC-1'
    control_name VARCHAR(500) NOT NULL,
    control_description TEXT,
    control_category VARCHAR(100), -- e.g., 'Access Control', 'Audit and Accountability'
    parent_control_id UUID REFERENCES compliance_controls(id),
    is_applicable BOOLEAN DEFAULT TRUE,
    priority VARCHAR(50), -- 'critical', 'high', 'medium', 'low'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(framework_id, control_id)
);

CREATE INDEX idx_compliance_controls_framework ON compliance_controls(framework_id);
CREATE INDEX idx_compliance_controls_category ON compliance_controls(control_category);
CREATE INDEX idx_compliance_controls_parent ON compliance_controls(parent_control_id);
CREATE INDEX idx_compliance_controls_priority ON compliance_controls(priority);

-- Control mappings (which SentinelGrid features satisfy controls)
CREATE TABLE IF NOT EXISTS control_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    control_id UUID NOT NULL REFERENCES compliance_controls(id) ON DELETE CASCADE,
    sentinelgrid_feature VARCHAR(255) NOT NULL, -- 'iam_agent_mfa', 'access_reviews', 'audit_logs', 'jml_workflows'
    feature_description TEXT,
    coverage_level VARCHAR(50) DEFAULT 'partial', -- 'full', 'partial', 'not_applicable'
    implementation_notes TEXT,
    evidence_sources TEXT[], -- ['access_review_reports', 'audit_logs', 'mfa_dashboard', 'jml_logs']
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(control_id, sentinelgrid_feature)
);

CREATE INDEX idx_control_mappings_control ON control_mappings(control_id);
CREATE INDEX idx_control_mappings_feature ON control_mappings(sentinelgrid_feature);
CREATE INDEX idx_control_mappings_coverage ON control_mappings(coverage_level);

-- Tenant control status (implementation status per tenant)
CREATE TABLE IF NOT EXISTS tenant_control_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL,
    control_id UUID NOT NULL REFERENCES compliance_controls(id) ON DELETE CASCADE,
    
    -- Implementation status
    implementation_status VARCHAR(50) DEFAULT 'not_implemented', -- 'implemented', 'partially', 'not_implemented', 'not_applicable'
    implementation_percentage INTEGER DEFAULT 0, -- 0-100
    
    -- Evidence
    evidence_collected BOOLEAN DEFAULT FALSE,
    evidence_ids UUID[], -- References to evidence_items
    
    -- Assessment
    last_assessed_at TIMESTAMPTZ,
    assessed_by TEXT,
    assessment_notes TEXT,
    
    -- Gaps and actions
    gaps_identified TEXT[],
    action_items TEXT[],
    target_completion_date DATE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(tenant_id, realm_name, control_id)
);

CREATE INDEX idx_tenant_control_status_tenant_realm ON tenant_control_status(tenant_id, realm_name);
CREATE INDEX idx_tenant_control_status_control ON tenant_control_status(control_id);
CREATE INDEX idx_tenant_control_status_implementation ON tenant_control_status(implementation_status);
CREATE INDEX idx_tenant_control_status_evidence ON tenant_control_status(evidence_collected);

-- Comments
COMMENT ON TABLE compliance_frameworks IS 'Supported compliance frameworks (SOC 2, NIST CSF, HIPAA, PCI DSS, CMMC)';
COMMENT ON TABLE compliance_controls IS 'Individual controls from each framework';
COMMENT ON TABLE control_mappings IS 'Mapping of SentinelGrid features to compliance controls';
COMMENT ON TABLE tenant_control_status IS 'Per-tenant implementation status of compliance controls';

