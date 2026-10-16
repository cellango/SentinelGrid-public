-- Schema-only migration: tenant compliance framework selections.

CREATE TABLE IF NOT EXISTS public.tenant_framework_selections (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    framework_id character varying(80) NOT NULL,
    status character varying(40) DEFAULT 'active'::character varying NOT NULL,
    priority integer,
    target_date date,
    selected_by text,
    selected_at timestamp with time zone DEFAULT now() NOT NULL,
    source character varying(80) DEFAULT 'manual'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT tenant_framework_selections_status_check
        CHECK ((status)::text = ANY (ARRAY[
            ('active'::character varying)::text,
            ('inactive'::character varying)::text,
            ('evaluating'::character varying)::text
        ]))
);

ALTER TABLE ONLY public.tenant_framework_selections
    ADD CONSTRAINT tenant_framework_selections_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.tenant_framework_selections
    ADD CONSTRAINT tenant_framework_selections_tenant_framework_key UNIQUE (tenant_id, framework_id);

ALTER TABLE ONLY public.tenant_framework_selections
    ADD CONSTRAINT tenant_framework_selections_tenant_id_fkey
    FOREIGN KEY (tenant_id) REFERENCES public.tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_tenant_framework_selections_tenant
    ON public.tenant_framework_selections USING btree (tenant_id);

CREATE INDEX IF NOT EXISTS idx_tenant_framework_selections_framework
    ON public.tenant_framework_selections USING btree (framework_id);

CREATE INDEX IF NOT EXISTS idx_tenant_framework_selections_status
    ON public.tenant_framework_selections USING btree (status);

CREATE TRIGGER update_tenant_framework_selections_updated_at
    BEFORE UPDATE ON public.tenant_framework_selections
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

ALTER TABLE public.tenant_framework_selections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_framework_selections FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_select ON public.tenant_framework_selections
    FOR SELECT USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_modify ON public.tenant_framework_selections
    FOR ALL USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY superadmin_bypass ON public.tenant_framework_selections
    USING (current_setting('app.is_superadmin', true) = 'true');

COMMENT ON TABLE public.tenant_framework_selections IS
    'Tenant-selected compliance frameworks. Onboarding trust profile can seed initial rows, but explicit selections are preserved.';

