-- Schema-only migration: evidence integrity verification and retention controls.

CREATE TABLE IF NOT EXISTS public.evidence_integrity_verifications (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    evidence_item_id uuid NOT NULL,
    verification_status character varying(50) NOT NULL,
    verification_method character varying(80) DEFAULT 'hash_compare'::character varying NOT NULL,
    expected_hash_sha256 character varying(64) NOT NULL,
    observed_hash_sha256 character varying(64),
    verified_by text NOT NULL,
    verified_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT evidence_integrity_verifications_pkey PRIMARY KEY (id),
    CONSTRAINT evidence_integrity_verifications_evidence_item_id_fkey
        FOREIGN KEY (evidence_item_id) REFERENCES public.evidence_items(id) ON DELETE CASCADE,
    CONSTRAINT evidence_integrity_verifications_status_check
        CHECK ((verification_status)::text = ANY (ARRAY[
            ('verified'::character varying)::text,
            ('mismatch'::character varying)::text,
            ('missing_observed_hash'::character varying)::text
        ])),
    CONSTRAINT evidence_integrity_verifications_expected_hash_check
        CHECK (expected_hash_sha256 ~* '^[0-9a-f]{64}$'),
    CONSTRAINT evidence_integrity_verifications_observed_hash_check
        CHECK (observed_hash_sha256 IS NULL OR observed_hash_sha256 ~* '^[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS public.evidence_retention_policies (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    framework_id uuid,
    subject_type character varying(50) NOT NULL,
    retention_days integer NOT NULL,
    policy_name character varying(255) NOT NULL,
    description text,
    legal_hold boolean DEFAULT false NOT NULL,
    created_by text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_by text,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    deleted_at timestamp with time zone,
    deleted_by text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT evidence_retention_policies_pkey PRIMARY KEY (id),
    CONSTRAINT evidence_retention_policies_framework_id_fkey
        FOREIGN KEY (framework_id) REFERENCES public.compliance_frameworks(id) ON DELETE SET NULL,
    CONSTRAINT evidence_retention_policies_subject_check
        CHECK ((subject_type)::text = ANY (ARRAY[
            ('evidence_item'::character varying)::text,
            ('evidence_package'::character varying)::text,
            ('evidence_export'::character varying)::text,
            ('collection_task'::character varying)::text
        ])),
    CONSTRAINT evidence_retention_policies_days_check
        CHECK (retention_days > 0),
    CONSTRAINT evidence_retention_policies_deleted_by_check
        CHECK (deleted_at IS NULL OR deleted_by IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_evidence_integrity_verifications_tenant_item
    ON public.evidence_integrity_verifications USING btree (tenant_id, evidence_item_id, verified_at DESC);

CREATE INDEX IF NOT EXISTS idx_evidence_integrity_verifications_status
    ON public.evidence_integrity_verifications USING btree (tenant_id, verification_status, verified_at DESC);

CREATE INDEX IF NOT EXISTS idx_evidence_retention_policies_tenant_subject
    ON public.evidence_retention_policies USING btree (tenant_id, subject_type);

CREATE INDEX IF NOT EXISTS idx_evidence_retention_policies_framework
    ON public.evidence_retention_policies USING btree (tenant_id, framework_id, subject_type)
    WHERE framework_id IS NOT NULL AND deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_retention_policies_default_unique
    ON public.evidence_retention_policies USING btree (tenant_id, subject_type)
    WHERE framework_id IS NULL AND deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_retention_policies_framework_unique
    ON public.evidence_retention_policies USING btree (tenant_id, framework_id, subject_type)
    WHERE framework_id IS NOT NULL AND deleted_at IS NULL;

DROP TRIGGER IF EXISTS update_evidence_retention_policies_updated_at ON public.evidence_retention_policies;
CREATE TRIGGER update_evidence_retention_policies_updated_at
    BEFORE UPDATE ON public.evidence_retention_policies
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE OR REPLACE FUNCTION public.prevent_completed_evidence_export_mutation()
RETURNS trigger AS $$
BEGIN
    IF OLD.status = 'completed'
       AND OLD.immutable_after IS NOT NULL
       AND (
           NEW.storage_uri IS DISTINCT FROM OLD.storage_uri
           OR NEW.hash_sha256 IS DISTINCT FROM OLD.hash_sha256
           OR NEW.file_size_bytes IS DISTINCT FROM OLD.file_size_bytes
           OR NEW.manifest IS DISTINCT FROM OLD.manifest
           OR NEW.status IS DISTINCT FROM OLD.status
       ) THEN
        RAISE EXCEPTION 'completed evidence exports are immutable';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS prevent_completed_evidence_export_mutation ON public.evidence_exports;
CREATE TRIGGER prevent_completed_evidence_export_mutation
    BEFORE UPDATE ON public.evidence_exports
    FOR EACH ROW EXECUTE FUNCTION public.prevent_completed_evidence_export_mutation();

ALTER TABLE public.evidence_integrity_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_integrity_verifications FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_select ON public.evidence_integrity_verifications
    FOR SELECT USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_modify ON public.evidence_integrity_verifications
    FOR ALL USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY superadmin_bypass ON public.evidence_integrity_verifications
    USING (current_setting('app.is_superadmin', true) = 'true');

ALTER TABLE public.evidence_retention_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_retention_policies FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_select ON public.evidence_retention_policies
    FOR SELECT USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_modify ON public.evidence_retention_policies
    FOR ALL USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY superadmin_bypass ON public.evidence_retention_policies
    USING (current_setting('app.is_superadmin', true) = 'true');

COMMENT ON TABLE public.evidence_integrity_verifications IS
    'Tenant-scoped evidence integrity verification events comparing observed artifact hashes to stored SHA-256 values.';

COMMENT ON TABLE public.evidence_retention_policies IS
    'Tenant and optional framework scoped retention rules for evidence items, packages, exports, and recollection tasks.';

COMMENT ON TRIGGER prevent_completed_evidence_export_mutation ON public.evidence_exports IS
    'Prevents artifact and manifest mutation after an evidence export is completed.';
