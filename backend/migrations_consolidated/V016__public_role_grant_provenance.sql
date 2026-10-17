SET search_path = public, pg_catalog;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

DO $roles$
BEGIN
    -- This IAM-only domain is absent from the separate shared catalog baseline.
    IF to_regclass('public.role_entitlement_patterns') IS NULL THEN RETURN; END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid='public.entitlements'::regclass
                   AND attname='granted_to_id' AND atttypid='uuid'::regtype AND NOT attisdropped) THEN
        RAISE EXCEPTION 'Unreviewed grant store; reconcile history before migration';
    END IF;
    -- Existing definitions/NULL global rows retain their data and remain opt-out.
    -- Unknown historical actors are not invented or backfilled.
    ALTER TABLE public.role_entitlement_patterns ADD COLUMN auto_grant boolean NOT NULL DEFAULT false;
    ALTER TABLE public.role_entitlement_patterns ADD COLUMN created_by uuid;

    CREATE TABLE public.iam_role_grants (
        id uuid PRIMARY KEY,
        tenant_id uuid NOT NULL,
        subject_id uuid NOT NULL,
        entitlement_id uuid NOT NULL,
        target jsonb NOT NULL,
        roles jsonb NOT NULL,
        pattern_ids jsonb NOT NULL,
        created_by uuid NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT iam_role_grant_unique UNIQUE (entitlement_id),
        CONSTRAINT iam_role_grant_entitlement FOREIGN KEY (entitlement_id) REFERENCES public.entitlements(id) ON DELETE CASCADE,
        CONSTRAINT iam_role_grant_json CHECK (jsonb_typeof(target)='object' AND jsonb_typeof(roles)='array' AND jsonb_typeof(pattern_ids)='array')
    );
    CREATE INDEX ix_iam_role_grant_subject ON public.iam_role_grants(tenant_id,subject_id);
    CREATE TRIGGER update_iam_role_grants_updated_at BEFORE UPDATE ON public.iam_role_grants
        FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
    ALTER TABLE public.iam_role_grants ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.iam_role_grants FORCE ROW LEVEL SECURITY;
    CREATE POLICY iam_role_grant_access ON public.iam_role_grants
        USING (tenant_id=public.iam_current_tenant_id()) WITH CHECK (tenant_id=public.iam_current_tenant_id());
    CREATE POLICY iam_role_grant_guard ON public.iam_role_grants AS RESTRICTIVE
        USING (tenant_id=public.iam_current_tenant_id() AND EXISTS (
            SELECT 1 FROM public.entitlements e WHERE e.id=entitlement_id AND e.tenant_id=iam_role_grants.tenant_id
                AND e.granted_to_type='user' AND e.granted_to_id=subject_id))
        WITH CHECK (tenant_id=public.iam_current_tenant_id() AND EXISTS (
            SELECT 1 FROM public.entitlements e WHERE e.id=entitlement_id AND e.tenant_id=iam_role_grants.tenant_id
                AND e.granted_to_type='user' AND e.granted_to_id=subject_id));
    REVOKE ALL ON public.iam_role_grants FROM PUBLIC;
    CREATE FUNCTION public.iam_guard_role_grant_target() RETURNS trigger
    LANGUAGE plpgsql SECURITY INVOKER SET search_path=pg_catalog,public AS $target$
    BEGIN
        IF ROW(OLD.tenant_id,OLD.resource_type,OLD.resource_id,OLD.action,OLD.granted_to_type,OLD.granted_to_id,OLD.granted_by,OLD.expires_at)
           IS DISTINCT FROM ROW(NEW.tenant_id,NEW.resource_type,NEW.resource_id,NEW.action,NEW.granted_to_type,NEW.granted_to_id,NEW.granted_by,NEW.expires_at)
           AND EXISTS (SELECT 1 FROM public.iam_role_grants b WHERE b.entitlement_id=OLD.id) THEN
            RAISE EXCEPTION 'Managed grant target is immutable; reconcile ownership' USING ERRCODE='23514';
        END IF;
        RETURN NEW;
    END
    $target$;
    CREATE TRIGGER guard_iam_role_grant_target BEFORE UPDATE ON public.entitlements
        FOR EACH ROW EXECUTE FUNCTION public.iam_guard_role_grant_target();

END
$roles$;
