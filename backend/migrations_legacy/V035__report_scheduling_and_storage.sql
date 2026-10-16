-- Migration: Report Scheduling and Storage
-- Date: 2025-12-02
-- Purpose: Professional compliance reports with scheduling, tenant isolation, and LLM integration

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Generated reports storage (tenant + realm scoped)
CREATE TABLE IF NOT EXISTS generated_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL, -- Keycloak realm
    report_type VARCHAR(100) NOT NULL, -- 'soc2_coverage', 'iam_mfa_hygiene', etc.
    report_name VARCHAR(500) NOT NULL, -- "SOC2_Coverage_Report_2025-12-02_AcmeCorp"
    report_period_start DATE,
    report_period_end DATE,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    generated_by TEXT, -- User ID or 'system' for scheduled
    
    -- File storage
    file_path_pdf TEXT, -- S3/local: s3://reports/{tenant_id}/{realm}/{report_name}.pdf
    file_path_csv TEXT, -- s3://reports/{tenant_id}/{realm}/{report_name}.csv
    file_size_bytes BIGINT,
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'generating', -- 'generating', 'ready', 'failed'
    error_message TEXT,
    
    -- LLM integration
    llm_ingested BOOLEAN DEFAULT FALSE,
    llm_document_id TEXT, -- Vector DB document ID
    llm_ingested_at TIMESTAMPTZ,
    
    -- Metadata
    metadata JSONB, -- Report-specific data (scores, counts, etc.)
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(tenant_id, realm_name, report_type, report_name)
);

CREATE INDEX idx_generated_reports_tenant_realm ON generated_reports(tenant_id, realm_name);
CREATE INDEX idx_generated_reports_type ON generated_reports(report_type);
CREATE INDEX idx_generated_reports_status ON generated_reports(status);
CREATE INDEX idx_generated_reports_llm ON generated_reports(llm_ingested);
CREATE INDEX idx_generated_reports_generated_at ON generated_reports(generated_at DESC);

-- Report schedules (per tenant + realm)
CREATE TABLE IF NOT EXISTS report_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL,
    report_type VARCHAR(100) NOT NULL,
    schedule_name VARCHAR(255),
    
    -- Scheduling
    cron_expression VARCHAR(100), -- '0 9 * * MON' for weekly Monday 9am
    timezone VARCHAR(50) DEFAULT 'UTC',
    
    -- Recipients
    recipients TEXT[], -- Email addresses to send report
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    last_run_status VARCHAR(50), -- 'success', 'failed'
    last_report_id UUID REFERENCES generated_reports(id),
    
    -- Audit
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(tenant_id, realm_name, report_type, schedule_name)
);

CREATE INDEX idx_report_schedules_tenant_realm ON report_schedules(tenant_id, realm_name);
CREATE INDEX idx_report_schedules_active ON report_schedules(is_active);
CREATE INDEX idx_report_schedules_next_run ON report_schedules(next_run_at);
CREATE INDEX idx_report_schedules_type ON report_schedules(report_type);

-- Report access audit (who viewed/downloaded)
CREATE TABLE IF NOT EXISTS report_access_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID REFERENCES generated_reports(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    realm_name VARCHAR(255) NOT NULL,
    user_id TEXT NOT NULL,
    user_email VARCHAR(255),
    access_type VARCHAR(50) NOT NULL, -- 'view', 'download_pdf', 'download_csv', 'llm_query'
    accessed_at TIMESTAMPTZ DEFAULT NOW(),
    ip_address INET,
    metadata JSONB -- For llm_query: {query: "...", response_preview: "..."}
);

CREATE INDEX idx_report_access_tenant_realm ON report_access_log(tenant_id, realm_name);
CREATE INDEX idx_report_access_user ON report_access_log(user_id);
CREATE INDEX idx_report_access_type ON report_access_log(access_type);
CREATE INDEX idx_report_access_report ON report_access_log(report_id);
CREATE INDEX idx_report_access_at ON report_access_log(accessed_at DESC);

-- Vector DB metadata (references to Qdrant/Pinecone documents)
CREATE TABLE IF NOT EXISTS report_llm_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID REFERENCES generated_reports(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL,
    realm_name VARCHAR(255) NOT NULL,
    vector_db_id TEXT NOT NULL, -- Qdrant/Pinecone document ID
    chunk_index INTEGER DEFAULT 0, -- If report split into chunks
    content_preview TEXT, -- First 500 chars
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(report_id, chunk_index)
);

CREATE INDEX idx_llm_docs_tenant_realm ON report_llm_documents(tenant_id, realm_name);
CREATE INDEX idx_llm_docs_vector_id ON report_llm_documents(vector_db_id);
CREATE INDEX idx_llm_docs_report ON report_llm_documents(report_id);

-- Comments for documentation
COMMENT ON TABLE generated_reports IS 'Stored compliance reports with tenant isolation and LLM integration';
COMMENT ON COLUMN generated_reports.report_name IS 'Date-stamped filename: ReportType_YYYY-MM-DD_TenantName';
COMMENT ON COLUMN generated_reports.llm_ingested IS 'Whether report has been ingested into vector DB for Q&A';
COMMENT ON TABLE report_schedules IS 'Automated report generation schedules per tenant';
COMMENT ON COLUMN report_schedules.cron_expression IS 'Cron expression for scheduling (e.g., 0 9 * * MON)';
COMMENT ON TABLE report_access_log IS 'Audit log for report viewing and downloading (compliance requirement)';
COMMENT ON TABLE report_llm_documents IS 'Vector DB document references for report Q&A with tenant isolation';

