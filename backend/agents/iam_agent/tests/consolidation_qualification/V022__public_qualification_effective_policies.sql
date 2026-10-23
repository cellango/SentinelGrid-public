-- Test-only target; excluded from all production migration profiles.
SET search_path = public, pg_catalog;
SET LOCAL lock_timeout = '5s';


CREATE TABLE public.policies (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    tenant_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    display_name character varying(255) NOT NULL,
    description text,
    policy_type character varying(100) NOT NULL,
    scope character varying(100) DEFAULT 'tenant'::character varying NOT NULL,
    scope_id uuid,
    policy_data jsonb NOT NULL,
    is_active boolean DEFAULT true,
    priority integer DEFAULT 100,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by text,
    is_template boolean DEFAULT false,
    approval_required boolean DEFAULT false,
    approval_status text DEFAULT 'approved'::text,
    CONSTRAINT ck_policies_approval_status CHECK ((approval_status = ANY (ARRAY['pending'::text, 'approved'::text, 'rejected'::text])))
);

ALTER TABLE public.policies ADD PRIMARY KEY (id);

CREATE TABLE public.policy_rules (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    policy_id uuid NOT NULL,
    rule_id character varying(255) NOT NULL,
    name character varying(255),
    description text,
    conditions jsonb NOT NULL,
    actions jsonb NOT NULL,
    priority integer DEFAULT 100,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.policy_rules ADD PRIMARY KEY (id);

ALTER TABLE public.policy_rules ADD CONSTRAINT qualification_policy_parent FOREIGN KEY (policy_id) REFERENCES public.policies(id);
ALTER TABLE public.policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.policies FORCE ROW LEVEL SECURITY;
CREATE POLICY qualification_access ON public.policies USING (tenant_id = public.iam_current_tenant_id()) WITH CHECK (tenant_id = public.iam_current_tenant_id());
CREATE POLICY qualification_guard ON public.policies AS RESTRICTIVE USING (tenant_id = public.iam_current_tenant_id()) WITH CHECK (tenant_id = public.iam_current_tenant_id());
ALTER TABLE public.policy_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.policy_rules FORCE ROW LEVEL SECURITY;
CREATE POLICY qualification_access ON public.policy_rules USING (EXISTS (SELECT 1 FROM public.policies p WHERE p.id = policy_id AND p.tenant_id = public.iam_current_tenant_id())) WITH CHECK (EXISTS (SELECT 1 FROM public.policies p WHERE p.id = policy_id AND p.tenant_id = public.iam_current_tenant_id()));
CREATE POLICY qualification_guard ON public.policy_rules AS RESTRICTIVE USING (EXISTS (SELECT 1 FROM public.policies p WHERE p.id = policy_id AND p.tenant_id = public.iam_current_tenant_id())) WITH CHECK (EXISTS (SELECT 1 FROM public.policies p WHERE p.id = policy_id AND p.tenant_id = public.iam_current_tenant_id()));
