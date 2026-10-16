-- Migration: Evidence Repository
-- Date: 2025-12-02
-- Purpose: Evidence collection and packaging for compliance audits

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Evidence packages
CREATE TABLE IF NOT EXISTS evidence_packages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL,
    package_name VARCHAR(255) NOT NULL,
    framework_id UUID REFERENCES compliance_frameworks(id),
    
    -- Period
    report_period_start DATE NOT NULL,
    report_period_end DATE NOT NULL,
    
    -- Creator
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Status
    status VARCHAR(50) DEFAULT 'collecting', -- 'collecting', 'ready', 'exported', 'archived'
    export_format VARCHAR(50), -- 'pdf', 'zip'
    file_path TEXT,
    file_size_bytes BIGINT,
    
    -- Metadata
    description TEXT,
    metadata JSONB,
    
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_evidence_packages_tenant_realm ON evidence_packages(tenant_id, realm_name);
CREATE INDEX idx_evidence_packages_framework ON evidence_packages(framework_id);
CREATE INDEX idx_evidence_packages_period ON evidence_packages(report_period_start, report_period_end);
CREATE INDEX idx_evidence_packages_status ON evidence_packages(status);

-- Evidence items
CREATE TABLE IF NOT EXISTS evidence_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    package_id UUID REFERENCES evidence_packages(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL,
    control_id UUID REFERENCES compliance_controls(id),
    
    -- Evidence details
    evidence_type VARCHAR(100) NOT NULL, -- 'screenshot', 'report', 'log_export', 'configuration', 'policy_document', 'test_result'
    evidence_title VARCHAR(500) NOT NULL,
    evidence_description TEXT,
    
    -- File information
    file_path TEXT,
    file_format VARCHAR(50), -- 'pdf', 'csv', 'json', 'png'
    file_size_bytes BIGINT,
    file_hash VARCHAR(64), -- SHA-256 for integrity
    
    -- Source information
    source_system VARCHAR(100), -- 'iam_agent', 'siem_agent', 'soar_agent', 'posture_agent'
    source_reference TEXT, -- Reference to source data (e.g., report_id, log_id)
    
    -- Collection details
    collected_at TIMESTAMPTZ DEFAULT NOW(),
    collected_by TEXT,
    
    -- Metadata
    metadata JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_evidence_items_package ON evidence_items(package_id);
CREATE INDEX idx_evidence_items_tenant_realm ON evidence_items(tenant_id, realm_name);
CREATE INDEX idx_evidence_items_control ON evidence_items(control_id);
CREATE INDEX idx_evidence_items_type ON evidence_items(evidence_type);
CREATE INDEX idx_evidence_items_source ON evidence_items(source_system);
CREATE INDEX idx_evidence_items_collected ON evidence_items(collected_at DESC);

-- Evidence collection tasks (automation)
CREATE TABLE IF NOT EXISTS evidence_collection_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL,
    package_id UUID REFERENCES evidence_packages(id) ON DELETE CASCADE,
    
    -- Task details
    task_name VARCHAR(255) NOT NULL,
    task_type VARCHAR(100), -- 'collect_access_reviews', 'export_audit_logs', 'snapshot_mfa_status'
    control_ids UUID[], -- Controls this task provides evidence for
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Results
    evidence_items_created UUID[], -- IDs of created evidence items
    error_message TEXT,
    
    -- Metadata
    metadata JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_evidence_tasks_tenant_realm ON evidence_collection_tasks(tenant_id, realm_name);
CREATE INDEX idx_evidence_tasks_package ON evidence_collection_tasks(package_id);
CREATE INDEX idx_evidence_tasks_status ON evidence_collection_tasks(status);
CREATE INDEX idx_evidence_tasks_type ON evidence_collection_tasks(task_type);

-- Comments
COMMENT ON TABLE evidence_packages IS 'Evidence packages for compliance audits';
COMMENT ON COLUMN evidence_packages.export_format IS 'Export format: pdf (single PDF), zip (multiple files)';
COMMENT ON TABLE evidence_items IS 'Individual evidence items (reports, logs, screenshots, configs)';
COMMENT ON COLUMN evidence_items.file_hash IS 'SHA-256 hash for evidence integrity verification';
COMMENT ON TABLE evidence_collection_tasks IS 'Automated evidence collection tasks';

