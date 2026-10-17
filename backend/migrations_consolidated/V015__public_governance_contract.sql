-- Additive governance compatibility for the separate, reviewed IAM V1 lineage.
-- The shared catalog profile has no audit_campaigns table and is unchanged.
SET search_path = public, pg_catalog;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

DO $governance$
BEGIN
    IF to_regclass('public.audit_campaigns') IS NULL THEN RETURN; END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid='public.audit_campaigns'::regclass
                   AND attname='scope' AND atttypid='jsonb'::regtype AND NOT attisdropped)
       OR NOT EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid='public.certifications'::regclass
                      AND attname='certifier_id' AND atttypid='uuid'::regtype AND NOT attisdropped) THEN
        RAISE EXCEPTION 'Unreviewed governance contract; reconcile history before migration';
    END IF;
    -- Existing JSON scope/config/schedule and all legacy statuses/decisions survive.
    -- For historical rows this is migration time, not a fabricated old update time.
    ALTER TABLE public.audit_campaigns ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now();
    CREATE TRIGGER update_audit_campaigns_updated_at BEFORE UPDATE ON public.audit_campaigns
        FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

    -- V014 already requires both parents in the authenticated tenant. Intersect it
    -- with the exact child link, so a history row cannot name another same-tenant grant.
    CREATE POLICY iam_history_link_guard ON public.certification_history AS RESTRICTIVE
        USING (EXISTS (SELECT 1 FROM public.certifications c
                       WHERE c.id=certification_id AND c.entitlement_id=certification_history.entitlement_id))
        WITH CHECK (EXISTS (SELECT 1 FROM public.certifications c
                            WHERE c.id=certification_id AND c.entitlement_id=certification_history.entitlement_id));
END
$governance$;
