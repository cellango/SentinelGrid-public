-- Additive in either reviewed physical database profile. Never converts the
-- shared app-catalog entitlements table into the separate IAM access-grant table.
SET search_path = public, pg_catalog;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

CREATE FUNCTION public.iam_current_tenant_id() RETURNS uuid
LANGUAGE plpgsql STABLE SECURITY INVOKER SET search_path = pg_catalog AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_tenant_id', true), '')::uuid;
EXCEPTION WHEN invalid_text_representation THEN
    RETURN NULL;
END;
$$;

-- A new name avoids incompatible legacy action/performed_at vs event_type shapes.
-- Snapshot IDs intentionally have no cascading FK: deleting a live record must
-- not delete its audit history. No legacy rows are moved, relabelled or fabricated.
CREATE TABLE public.iam_audit_events (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    event_type varchar(50) NOT NULL,
    entitlement_id uuid,
    performed_by uuid,
    actor_type varchar(30) NOT NULL DEFAULT 'user',
    subject_id uuid,
    decision varchar(10),
    performed_by_name varchar(255),
    changes jsonb NOT NULL DEFAULT '{}'::jsonb,
    reason text,
    campaign_id uuid,
    certification_id uuid,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT iam_audit_actor_type CHECK (actor_type IN ('user', 'internal_service')),
    CONSTRAINT iam_audit_user_actor CHECK (actor_type <> 'user' OR performed_by IS NOT NULL),
    CONSTRAINT iam_audit_decision CHECK (decision IS NULL OR decision IN ('allow', 'deny'))
);
CREATE INDEX ix_iam_audit_tenant_created ON public.iam_audit_events (tenant_id, created_at);
ALTER TABLE public.iam_audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.iam_audit_events FORCE ROW LEVEL SECURITY;
CREATE POLICY iam_audit_read ON public.iam_audit_events FOR SELECT
    USING (tenant_id = public.iam_current_tenant_id());
CREATE POLICY iam_audit_append ON public.iam_audit_events FOR INSERT
    WITH CHECK (tenant_id = public.iam_current_tenant_id());
CREATE POLICY iam_audit_guard ON public.iam_audit_events AS RESTRICTIVE
    USING (tenant_id = public.iam_current_tenant_id())
    WITH CHECK (tenant_id = public.iam_current_tenant_id());
CREATE POLICY iam_audit_no_update ON public.iam_audit_events AS RESTRICTIVE FOR UPDATE
    USING (false) WITH CHECK (false);
CREATE POLICY iam_audit_no_delete ON public.iam_audit_events AS RESTRICTIVE FOR DELETE
    USING (false);
REVOKE ALL ON public.iam_audit_events FROM PUBLIC;

-- Restrictive policies intersect any existing permissive policies, including
-- V003's app.is_superadmin flag. Never rely on merely adding another OR policy.
DO $guards$
DECLARE
    table_name text;
    predicate text;
    tenant_column text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'entitlements', 'audit_campaigns', 'audit_schedules', 'role_entitlement_patterns',
        'tenant_references', 'access_requests', 'user_entitlements', 'policies', 'policy_evaluations'
    ] LOOP
        IF to_regclass('public.' || table_name) IS NULL THEN CONTINUE; END IF;
        tenant_column := CASE WHEN table_name = 'tenant_references' THEN 'id' ELSE 'tenant_id' END;
        IF NOT EXISTS (SELECT 1 FROM pg_attribute
                       WHERE attrelid = to_regclass('public.' || table_name)
                       AND attname = tenant_column AND atttypid = 'uuid'::regtype AND NOT attisdropped) THEN
            RAISE EXCEPTION 'Unreviewed tenant contract for public.%', table_name;
        END IF;
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', table_name);
        predicate := format('%I = public.iam_current_tenant_id()', tenant_column);
        EXECUTE format('CREATE POLICY iam_tenant_access ON public.%I USING (%s) WITH CHECK (%s)', table_name, predicate, predicate);
        EXECUTE format('CREATE POLICY iam_tenant_guard ON public.%I AS RESTRICTIVE USING (%s) WITH CHECK (%s)', table_name, predicate, predicate);
    END LOOP;

    FOR table_name, predicate IN SELECT * FROM (VALUES
        ('policy_rules', 'EXISTS (SELECT 1 FROM public.policies p WHERE p.id = policy_id AND p.tenant_id = public.iam_current_tenant_id())'),
        ('access_request_history', 'EXISTS (SELECT 1 FROM public.access_requests p WHERE p.id = request_id AND p.tenant_id = public.iam_current_tenant_id())'),
        ('certifications', 'EXISTS (SELECT 1 FROM public.audit_campaigns p WHERE p.id = campaign_id AND p.tenant_id = public.iam_current_tenant_id()) AND EXISTS (SELECT 1 FROM public.entitlements e WHERE e.id = entitlement_id AND e.tenant_id = public.iam_current_tenant_id())'),
        ('certification_history', 'EXISTS (SELECT 1 FROM public.certifications c JOIN public.audit_campaigns p ON p.id = c.campaign_id WHERE c.id = certification_id AND p.tenant_id = public.iam_current_tenant_id()) AND EXISTS (SELECT 1 FROM public.entitlements e WHERE e.id = entitlement_id AND e.tenant_id = public.iam_current_tenant_id())'),
        ('entitlement_audit_log', 'EXISTS (SELECT 1 FROM public.entitlements e WHERE e.id = entitlement_id AND e.tenant_id = public.iam_current_tenant_id())')
    ) AS child(name, expression) LOOP
        IF to_regclass('public.' || table_name) IS NULL THEN CONTINUE; END IF;
        IF table_name = 'entitlement_audit_log' AND EXISTS (
            SELECT 1 FROM pg_attribute WHERE attrelid = to_regclass('public.entitlement_audit_log')
            AND attname = 'tenant_id' AND atttypid = 'uuid'::regtype AND NOT attisdropped
        ) THEN predicate := 'tenant_id = public.iam_current_tenant_id()'; END IF;
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', table_name);
        EXECUTE format('CREATE POLICY iam_parent_access ON public.%I USING (%s) WITH CHECK (%s)', table_name, predicate, predicate);
        EXECUTE format('CREATE POLICY iam_parent_guard ON public.%I AS RESTRICTIVE USING (%s) WITH CHECK (%s)', table_name, predicate, predicate);
    END LOOP;
END
$guards$;
