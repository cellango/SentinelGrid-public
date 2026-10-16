-- Schema-only migration: tenant preferences used by compliance launch controls.
-- tenant_service can create this table opportunistically in older environments;
-- this migration makes the contract explicit for launch readiness.

CREATE TABLE IF NOT EXISTS public.tenant_preferences (
    tenant_id uuid PRIMARY KEY REFERENCES public.tenants(id) ON DELETE CASCADE,
    alert_preferences jsonb NOT NULL DEFAULT '{}'::jsonb,
    feature_flags jsonb NOT NULL DEFAULT '{}'::jsonb,
    notification_email text,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

COMMENT ON TABLE public.tenant_preferences IS
    'Tenant-scoped preferences and feature flags. Compliance launch controls use feature_flags compliance_* keys.';

COMMENT ON COLUMN public.tenant_preferences.feature_flags IS
    'Tenant feature flags such as compliance_multi_framework_enabled, compliance_evidence_repository_enabled, and compliance_agent_enabled.';

ALTER TABLE public.tenant_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_preferences FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_preferences_isolation_select ON public.tenant_preferences
    FOR SELECT USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_preferences_isolation_modify ON public.tenant_preferences
    FOR ALL USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY tenant_preferences_superadmin_bypass ON public.tenant_preferences
    USING (current_setting('app.is_superadmin', true) = 'true');
