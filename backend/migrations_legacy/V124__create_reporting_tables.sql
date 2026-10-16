-- Create base reporting tables used by reporting_service.

CREATE TABLE IF NOT EXISTS reporting.reports (
    id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR NOT NULL,
    template_id VARCHAR NULL REFERENCES reporting.report_templates(id),
    name VARCHAR NOT NULL,
    format VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    generated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    generated_by VARCHAR NULL,
    date_range_start TIMESTAMP WITHOUT TIME ZONE NULL,
    date_range_end TIMESTAMP WITHOUT TIME ZONE NULL,
    file_path VARCHAR NULL,
    file_size_bytes INTEGER NULL,
    download_url VARCHAR NULL,
    sections JSON NULL,
    metadata JSON NULL,
    error_message TEXT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reports_tenant_id ON reporting.reports(tenant_id);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reporting.reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reporting.reports(created_at DESC);

CREATE TABLE IF NOT EXISTS reporting.report_shares (
    id VARCHAR PRIMARY KEY,
    report_id VARCHAR NOT NULL REFERENCES reporting.reports(id) ON DELETE CASCADE,
    tenant_id VARCHAR NOT NULL,
    share_token VARCHAR UNIQUE NOT NULL,
    expires_at TIMESTAMP WITHOUT TIME ZONE NULL,
    password_hash VARCHAR NULL,
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP WITHOUT TIME ZONE NULL,
    created_by VARCHAR NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_report_shares_tenant_id ON reporting.report_shares(tenant_id);
CREATE INDEX IF NOT EXISTS idx_report_shares_report_id ON reporting.report_shares(report_id);

-- Compatibility views in public for legacy consumers.
CREATE OR REPLACE VIEW public.reports AS SELECT * FROM reporting.reports;
CREATE OR REPLACE VIEW public.report_shares AS SELECT * FROM reporting.report_shares;
