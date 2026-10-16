-- Schema-only migration: supervised Compliance Agent recommendations.

CREATE TABLE IF NOT EXISTS public.compliance_agent_recommendations (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    agent_task_id text,
    trigger_type character varying(120) NOT NULL,
    recommendation_type character varying(120) NOT NULL,
    state character varying(50) DEFAULT 'proposed'::character varying NOT NULL,
    priority character varying(50) DEFAULT 'medium'::character varying NOT NULL,
    source_type character varying(120) NOT NULL,
    source_id text,
    framework_id text,
    control_id text,
    evidence_item_id text,
    evidence_package_id text,
    report_id text,
    title text NOT NULL,
    summary text NOT NULL,
    proposed_actions jsonb DEFAULT '[]'::jsonb NOT NULL,
    requires_approval boolean DEFAULT true NOT NULL,
    created_by text,
    decided_by text,
    decided_at timestamp with time zone,
    decision_notes text,
    superseded_by uuid,
    idempotency_key text NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    CONSTRAINT compliance_agent_recommendations_pkey PRIMARY KEY (id),
    CONSTRAINT compliance_agent_recommendations_state_check
        CHECK ((state)::text = ANY (ARRAY[
            ('draft'::character varying)::text,
            ('proposed'::character varying)::text,
            ('accepted'::character varying)::text,
            ('rejected'::character varying)::text,
            ('superseded'::character varying)::text
        ])),
    CONSTRAINT compliance_agent_recommendations_priority_check
        CHECK ((priority)::text = ANY (ARRAY[
            ('critical'::character varying)::text,
            ('high'::character varying)::text,
            ('medium'::character varying)::text,
            ('low'::character varying)::text
        ])),
    CONSTRAINT compliance_agent_recommendations_decision_check
        CHECK (
            state NOT IN ('accepted', 'rejected', 'superseded')
            OR decided_by IS NOT NULL
        ),
    CONSTRAINT compliance_agent_recommendations_superseded_fkey
        FOREIGN KEY (superseded_by)
        REFERENCES public.compliance_agent_recommendations(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_compliance_agent_recommendations_idempotency
    ON public.compliance_agent_recommendations USING btree (tenant_id, idempotency_key)
    WHERE deleted_at IS NULL AND state IN ('draft', 'proposed');

CREATE INDEX IF NOT EXISTS idx_compliance_agent_recommendations_tenant_state
    ON public.compliance_agent_recommendations USING btree (tenant_id, state, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_compliance_agent_recommendations_source
    ON public.compliance_agent_recommendations USING btree (
        tenant_id,
        source_type,
        source_id,
        created_at DESC
    )
    WHERE deleted_at IS NULL;

DROP TRIGGER IF EXISTS update_compliance_agent_recommendations_updated_at
    ON public.compliance_agent_recommendations;
CREATE TRIGGER update_compliance_agent_recommendations_updated_at
    BEFORE UPDATE ON public.compliance_agent_recommendations
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

ALTER TABLE public.compliance_agent_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.compliance_agent_recommendations FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_select ON public.compliance_agent_recommendations
    FOR SELECT USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_modify ON public.compliance_agent_recommendations
    FOR ALL USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY superadmin_bypass ON public.compliance_agent_recommendations
    USING (current_setting('app.is_superadmin', true) = 'true');

COMMENT ON TABLE public.compliance_agent_recommendations IS
    'Reviewable Compliance Agent recommendations and supervised task links scoped by tenant.';

COMMENT ON COLUMN public.compliance_agent_recommendations.idempotency_key IS
    'Tenant-scoped key used to avoid duplicate open recommendations for repeated trigger observations.';
