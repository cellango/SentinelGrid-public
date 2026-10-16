-- Move reporting tables into reporting schema with compatibility views.
-- Assumes reporting schema exists (V117).

-- Move tables
ALTER TABLE IF EXISTS generated_reports SET SCHEMA reporting;
ALTER TABLE IF EXISTS report_schedules SET SCHEMA reporting;
ALTER TABLE IF EXISTS report_access_log SET SCHEMA reporting;
ALTER TABLE IF EXISTS report_llm_documents SET SCHEMA reporting;

-- Compatibility views in public
CREATE OR REPLACE VIEW public.generated_reports AS SELECT * FROM reporting.generated_reports;
CREATE OR REPLACE VIEW public.report_schedules AS SELECT * FROM reporting.report_schedules;
CREATE OR REPLACE VIEW public.report_access_log AS SELECT * FROM reporting.report_access_log;
CREATE OR REPLACE VIEW public.report_llm_documents AS SELECT * FROM reporting.report_llm_documents;
