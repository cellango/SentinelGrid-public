-- Move audit tables into audit schema and create compatibility views in public.
-- Assumes audit schema exists (V117).

ALTER TABLE IF EXISTS platform_audit_logs SET SCHEMA audit;
ALTER TABLE IF EXISTS audit_log_statistics SET SCHEMA audit;
ALTER TABLE IF EXISTS audit_retention_policies SET SCHEMA audit;

-- Compatibility views in public so existing queries continue to work
CREATE OR REPLACE VIEW public.platform_audit_logs AS SELECT * FROM audit.platform_audit_logs;
CREATE OR REPLACE VIEW public.audit_log_statistics AS SELECT * FROM audit.audit_log_statistics;
CREATE OR REPLACE VIEW public.audit_retention_policies AS SELECT * FROM audit.audit_retention_policies;
