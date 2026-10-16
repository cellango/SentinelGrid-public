-- Create report_templates table in reporting schema for template definitions and scheduling.
CREATE TABLE IF NOT EXISTS reporting.report_templates (
    id VARCHAR PRIMARY KEY,
    tenant_id VARCHAR NULL,
    name VARCHAR NOT NULL,
    description TEXT NULL,
    type VARCHAR NOT NULL,
    sections JSON NOT NULL,
    data_queries JSON NULL,
    schedule JSON NULL,
    required_roles JSON NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_report_templates_tenant_id ON reporting.report_templates(tenant_id);

-- Compatibility view in public for legacy consumers.
CREATE OR REPLACE VIEW public.report_templates AS SELECT * FROM reporting.report_templates;
