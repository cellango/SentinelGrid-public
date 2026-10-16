-- Schema-only migration: durable compliance evidence repository lifecycle.
-- V001 included legacy evidence tables. This migration normalizes those tables
-- and adds the missing link, review, and export tables needed by the Compliance
-- evidence repository API in later slices.

ALTER TABLE public.evidence_items
    ADD COLUMN IF NOT EXISTS source_resource_id text,
    ADD COLUMN IF NOT EXISTS collector text,
    ADD COLUMN IF NOT EXISTS collection_method character varying(80),
    ADD COLUMN IF NOT EXISTS valid_from timestamp with time zone,
    ADD COLUMN IF NOT EXISTS valid_until timestamp with time zone,
    ADD COLUMN IF NOT EXISTS hash_sha256 character varying(64),
    ADD COLUMN IF NOT EXISTS storage_uri text,
    ADD COLUMN IF NOT EXISTS summary text,
    ADD COLUMN IF NOT EXISTS sensitivity character varying(50) DEFAULT 'internal'::character varying NOT NULL,
    ADD COLUMN IF NOT EXISTS review_status character varying(50) DEFAULT 'pending'::character varying NOT NULL,
    ADD COLUMN IF NOT EXISTS created_by text,
    ADD COLUMN IF NOT EXISTS updated_by text,
    ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone DEFAULT now() NOT NULL,
    ADD COLUMN IF NOT EXISTS deleted_at timestamp with time zone,
    ADD COLUMN IF NOT EXISTS deleted_by text,
    ADD COLUMN IF NOT EXISTS retention_until timestamp with time zone,
    ADD COLUMN IF NOT EXISTS immutable_after timestamp with time zone,
    ADD COLUMN IF NOT EXISTS provenance jsonb DEFAULT '{}'::jsonb NOT NULL,
    ADD COLUMN IF NOT EXISTS integrity_metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    ADD COLUMN IF NOT EXISTS chain_of_custody jsonb DEFAULT '[]'::jsonb NOT NULL;

ALTER TABLE public.evidence_items
    DROP CONSTRAINT IF EXISTS evidence_items_required_fields_check,
    DROP CONSTRAINT IF EXISTS evidence_items_sensitivity_check,
    DROP CONSTRAINT IF EXISTS evidence_items_review_status_check,
    DROP CONSTRAINT IF EXISTS evidence_items_collection_window_check,
    DROP CONSTRAINT IF EXISTS evidence_items_hash_sha256_check,
    DROP CONSTRAINT IF EXISTS evidence_items_deleted_by_check;

ALTER TABLE public.evidence_items
    ADD CONSTRAINT evidence_items_required_fields_check
    CHECK (
        tenant_id IS NOT NULL
        AND source_system IS NOT NULL
        AND btrim((source_system)::text) <> ''
        AND source_resource_id IS NOT NULL
        AND btrim(source_resource_id) <> ''
        AND collector IS NOT NULL
        AND btrim(collector) <> ''
        AND collection_method IS NOT NULL
        AND btrim((collection_method)::text) <> ''
        AND collected_at IS NOT NULL
        AND valid_from IS NOT NULL
        AND valid_until IS NOT NULL
        AND hash_sha256 IS NOT NULL
        AND storage_uri IS NOT NULL
        AND btrim(storage_uri) <> ''
        AND summary IS NOT NULL
        AND btrim(summary) <> ''
        AND sensitivity IS NOT NULL
        AND review_status IS NOT NULL
        AND created_by IS NOT NULL
        AND btrim(created_by) <> ''
    ) NOT VALID,
    ADD CONSTRAINT evidence_items_sensitivity_check
    CHECK ((sensitivity)::text = ANY (ARRAY[
        ('public'::character varying)::text,
        ('internal'::character varying)::text,
        ('confidential'::character varying)::text,
        ('restricted'::character varying)::text
    ])) NOT VALID,
    ADD CONSTRAINT evidence_items_review_status_check
    CHECK ((review_status)::text = ANY (ARRAY[
        ('pending'::character varying)::text,
        ('ready_for_review'::character varying)::text,
        ('accepted'::character varying)::text,
        ('rejected'::character varying)::text,
        ('needs_changes'::character varying)::text,
        ('expired'::character varying)::text,
        ('retired'::character varying)::text,
        ('superseded'::character varying)::text
    ])) NOT VALID,
    ADD CONSTRAINT evidence_items_collection_window_check
    CHECK (valid_until > valid_from) NOT VALID,
    ADD CONSTRAINT evidence_items_hash_sha256_check
    CHECK (hash_sha256 ~* '^[0-9a-f]{64}$') NOT VALID,
    ADD CONSTRAINT evidence_items_deleted_by_check
    CHECK (deleted_at IS NULL OR deleted_by IS NOT NULL) NOT VALID;

ALTER TABLE public.evidence_packages
    ADD COLUMN IF NOT EXISTS package_type character varying(80) DEFAULT 'audit_package'::character varying NOT NULL,
    ADD COLUMN IF NOT EXISTS summary text,
    ADD COLUMN IF NOT EXISTS storage_uri text,
    ADD COLUMN IF NOT EXISTS hash_sha256 character varying(64),
    ADD COLUMN IF NOT EXISTS sensitivity character varying(50) DEFAULT 'internal'::character varying NOT NULL,
    ADD COLUMN IF NOT EXISTS review_status character varying(50) DEFAULT 'pending'::character varying NOT NULL,
    ADD COLUMN IF NOT EXISTS finalized_at timestamp with time zone,
    ADD COLUMN IF NOT EXISTS finalized_by text,
    ADD COLUMN IF NOT EXISTS exported_at timestamp with time zone,
    ADD COLUMN IF NOT EXISTS exported_by text,
    ADD COLUMN IF NOT EXISTS deleted_at timestamp with time zone,
    ADD COLUMN IF NOT EXISTS deleted_by text,
    ADD COLUMN IF NOT EXISTS retention_until timestamp with time zone,
    ADD COLUMN IF NOT EXISTS immutable_after timestamp with time zone,
    ADD COLUMN IF NOT EXISTS manifest jsonb DEFAULT '{}'::jsonb NOT NULL,
    ADD COLUMN IF NOT EXISTS coverage_snapshot jsonb DEFAULT '{}'::jsonb NOT NULL;

ALTER TABLE public.evidence_packages
    DROP CONSTRAINT IF EXISTS evidence_packages_status_check,
    DROP CONSTRAINT IF EXISTS evidence_packages_sensitivity_check,
    DROP CONSTRAINT IF EXISTS evidence_packages_review_status_check,
    DROP CONSTRAINT IF EXISTS evidence_packages_period_check,
    DROP CONSTRAINT IF EXISTS evidence_packages_hash_sha256_check,
    DROP CONSTRAINT IF EXISTS evidence_packages_deleted_by_check;

ALTER TABLE public.evidence_packages
    ADD CONSTRAINT evidence_packages_status_check
    CHECK ((status)::text = ANY (ARRAY[
        ('collecting'::character varying)::text,
        ('ready_for_review'::character varying)::text,
        ('accepted'::character varying)::text,
        ('rejected'::character varying)::text,
        ('exported'::character varying)::text,
        ('archived'::character varying)::text,
        ('failed'::character varying)::text,
        ('deleted'::character varying)::text
    ])) NOT VALID,
    ADD CONSTRAINT evidence_packages_sensitivity_check
    CHECK ((sensitivity)::text = ANY (ARRAY[
        ('public'::character varying)::text,
        ('internal'::character varying)::text,
        ('confidential'::character varying)::text,
        ('restricted'::character varying)::text
    ])) NOT VALID,
    ADD CONSTRAINT evidence_packages_review_status_check
    CHECK ((review_status)::text = ANY (ARRAY[
        ('pending'::character varying)::text,
        ('ready_for_review'::character varying)::text,
        ('accepted'::character varying)::text,
        ('rejected'::character varying)::text,
        ('needs_changes'::character varying)::text,
        ('expired'::character varying)::text,
        ('retired'::character varying)::text,
        ('superseded'::character varying)::text
    ])) NOT VALID,
    ADD CONSTRAINT evidence_packages_period_check
    CHECK (report_period_end >= report_period_start) NOT VALID,
    ADD CONSTRAINT evidence_packages_hash_sha256_check
    CHECK (hash_sha256 IS NULL OR hash_sha256 ~* '^[0-9a-f]{64}$') NOT VALID,
    ADD CONSTRAINT evidence_packages_deleted_by_check
    CHECK (deleted_at IS NULL OR deleted_by IS NOT NULL) NOT VALID;

ALTER TABLE public.evidence_collection_tasks
    ADD COLUMN IF NOT EXISTS evidence_requirement_id uuid,
    ADD COLUMN IF NOT EXISTS source_system character varying(120),
    ADD COLUMN IF NOT EXISTS source_resource_id text,
    ADD COLUMN IF NOT EXISTS collector text,
    ADD COLUMN IF NOT EXISTS collection_method character varying(80),
    ADD COLUMN IF NOT EXISTS requested_by text,
    ADD COLUMN IF NOT EXISTS scheduled_for timestamp with time zone,
    ADD COLUMN IF NOT EXISTS due_at timestamp with time zone,
    ADD COLUMN IF NOT EXISTS last_attempt_at timestamp with time zone,
    ADD COLUMN IF NOT EXISTS retry_count integer DEFAULT 0 NOT NULL,
    ADD COLUMN IF NOT EXISTS created_by text,
    ADD COLUMN IF NOT EXISTS updated_by text,
    ADD COLUMN IF NOT EXISTS deleted_at timestamp with time zone,
    ADD COLUMN IF NOT EXISTS deleted_by text,
    ADD COLUMN IF NOT EXISTS retention_until timestamp with time zone;

ALTER TABLE public.evidence_collection_tasks
    DROP CONSTRAINT IF EXISTS evidence_collection_tasks_requirement_id_fkey,
    DROP CONSTRAINT IF EXISTS evidence_collection_tasks_status_check,
    DROP CONSTRAINT IF EXISTS evidence_collection_tasks_retry_count_check,
    DROP CONSTRAINT IF EXISTS evidence_collection_tasks_deleted_by_check;

ALTER TABLE public.evidence_collection_tasks
    ADD CONSTRAINT evidence_collection_tasks_requirement_id_fkey
    FOREIGN KEY (evidence_requirement_id)
    REFERENCES public.control_evidence_requirements(id) ON DELETE SET NULL,
    ADD CONSTRAINT evidence_collection_tasks_status_check
    CHECK ((status)::text = ANY (ARRAY[
        ('pending'::character varying)::text,
        ('running'::character varying)::text,
        ('completed'::character varying)::text,
        ('failed'::character varying)::text,
        ('cancelled'::character varying)::text,
        ('needs_connector'::character varying)::text,
        ('manual_evidence_required'::character varying)::text
    ])) NOT VALID,
    ADD CONSTRAINT evidence_collection_tasks_retry_count_check
    CHECK (retry_count >= 0) NOT VALID,
    ADD CONSTRAINT evidence_collection_tasks_deleted_by_check
    CHECK (deleted_at IS NULL OR deleted_by IS NOT NULL) NOT VALID;

CREATE TABLE IF NOT EXISTS public.evidence_control_links (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    evidence_item_id uuid NOT NULL,
    control_id uuid NOT NULL,
    evidence_requirement_id uuid,
    framework_id uuid,
    package_id uuid,
    link_type character varying(50) DEFAULT 'supports'::character varying NOT NULL,
    status character varying(50) DEFAULT 'active'::character varying NOT NULL,
    linked_by text NOT NULL,
    linked_at timestamp with time zone DEFAULT now() NOT NULL,
    rationale text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by text,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_by text,
    deleted_at timestamp with time zone,
    deleted_by text,
    retention_until timestamp with time zone,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT evidence_control_links_pkey PRIMARY KEY (id),
    CONSTRAINT evidence_control_links_evidence_item_id_fkey
        FOREIGN KEY (evidence_item_id) REFERENCES public.evidence_items(id) ON DELETE CASCADE,
    CONSTRAINT evidence_control_links_control_id_fkey
        FOREIGN KEY (control_id) REFERENCES public.compliance_controls(id),
    CONSTRAINT evidence_control_links_evidence_requirement_id_fkey
        FOREIGN KEY (evidence_requirement_id) REFERENCES public.control_evidence_requirements(id) ON DELETE SET NULL,
    CONSTRAINT evidence_control_links_framework_id_fkey
        FOREIGN KEY (framework_id) REFERENCES public.compliance_frameworks(id),
    CONSTRAINT evidence_control_links_package_id_fkey
        FOREIGN KEY (package_id) REFERENCES public.evidence_packages(id) ON DELETE SET NULL,
    CONSTRAINT evidence_control_links_link_type_check
        CHECK ((link_type)::text = ANY (ARRAY[
            ('supports'::character varying)::text,
            ('contradicts'::character varying)::text,
            ('context'::character varying)::text,
            ('exception'::character varying)::text
        ])),
    CONSTRAINT evidence_control_links_status_check
        CHECK ((status)::text = ANY (ARRAY[
            ('active'::character varying)::text,
            ('inactive'::character varying)::text,
            ('superseded'::character varying)::text,
            ('deleted'::character varying)::text
        ])),
    CONSTRAINT evidence_control_links_deleted_by_check
        CHECK (deleted_at IS NULL OR deleted_by IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS public.evidence_reviews (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    evidence_item_id uuid,
    package_id uuid,
    control_link_id uuid,
    review_status character varying(50) NOT NULL,
    reviewer text NOT NULL,
    reviewed_at timestamp with time zone DEFAULT now() NOT NULL,
    review_notes text,
    rejection_reason text,
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    created_by text NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_by text,
    deleted_at timestamp with time zone,
    deleted_by text,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT evidence_reviews_pkey PRIMARY KEY (id),
    CONSTRAINT evidence_reviews_evidence_item_id_fkey
        FOREIGN KEY (evidence_item_id) REFERENCES public.evidence_items(id) ON DELETE CASCADE,
    CONSTRAINT evidence_reviews_package_id_fkey
        FOREIGN KEY (package_id) REFERENCES public.evidence_packages(id) ON DELETE CASCADE,
    CONSTRAINT evidence_reviews_control_link_id_fkey
        FOREIGN KEY (control_link_id) REFERENCES public.evidence_control_links(id) ON DELETE CASCADE,
    CONSTRAINT evidence_reviews_target_check
        CHECK (evidence_item_id IS NOT NULL OR package_id IS NOT NULL OR control_link_id IS NOT NULL),
    CONSTRAINT evidence_reviews_status_check
        CHECK ((review_status)::text = ANY (ARRAY[
            ('accepted'::character varying)::text,
            ('rejected'::character varying)::text,
            ('needs_changes'::character varying)::text,
            ('expired'::character varying)::text,
            ('retired'::character varying)::text
        ])),
    CONSTRAINT evidence_reviews_deleted_by_check
        CHECK (deleted_at IS NULL OR deleted_by IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS public.evidence_exports (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_id uuid NOT NULL,
    package_id uuid NOT NULL,
    export_format character varying(50) NOT NULL,
    status character varying(50) DEFAULT 'requested'::character varying NOT NULL,
    requested_by text NOT NULL,
    requested_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    storage_uri text,
    hash_sha256 character varying(64),
    file_size_bytes bigint,
    include_sensitive boolean DEFAULT false NOT NULL,
    manifest jsonb DEFAULT '{}'::jsonb NOT NULL,
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_by text,
    deleted_at timestamp with time zone,
    deleted_by text,
    retention_until timestamp with time zone,
    immutable_after timestamp with time zone,
    metadata jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT evidence_exports_pkey PRIMARY KEY (id),
    CONSTRAINT evidence_exports_package_id_fkey
        FOREIGN KEY (package_id) REFERENCES public.evidence_packages(id) ON DELETE CASCADE,
    CONSTRAINT evidence_exports_format_check
        CHECK ((export_format)::text = ANY (ARRAY[
            ('pdf'::character varying)::text,
            ('zip'::character varying)::text,
            ('csv'::character varying)::text,
            ('json'::character varying)::text
        ])),
    CONSTRAINT evidence_exports_status_check
        CHECK ((status)::text = ANY (ARRAY[
            ('requested'::character varying)::text,
            ('running'::character varying)::text,
            ('completed'::character varying)::text,
            ('failed'::character varying)::text,
            ('expired'::character varying)::text,
            ('deleted'::character varying)::text
        ])),
    CONSTRAINT evidence_exports_hash_sha256_check
        CHECK (hash_sha256 IS NULL OR hash_sha256 ~* '^[0-9a-f]{64}$'),
    CONSTRAINT evidence_exports_completed_integrity_check
        CHECK ((status)::text <> 'completed' OR (storage_uri IS NOT NULL AND hash_sha256 IS NOT NULL)),
    CONSTRAINT evidence_exports_deleted_by_check
        CHECK (deleted_at IS NULL OR deleted_by IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_evidence_items_source_resource
    ON public.evidence_items USING btree (source_system, source_resource_id);

CREATE INDEX IF NOT EXISTS idx_evidence_items_review_status
    ON public.evidence_items USING btree (review_status);

CREATE INDEX IF NOT EXISTS idx_evidence_items_valid_until
    ON public.evidence_items USING btree (valid_until);

CREATE INDEX IF NOT EXISTS idx_evidence_items_hash_sha256
    ON public.evidence_items USING btree (hash_sha256);

CREATE INDEX IF NOT EXISTS idx_evidence_items_active
    ON public.evidence_items USING btree (tenant_id, review_status, valid_until)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_evidence_packages_active
    ON public.evidence_packages USING btree (tenant_id, status, review_status)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_evidence_packages_retention
    ON public.evidence_packages USING btree (retention_until);

CREATE INDEX IF NOT EXISTS idx_evidence_tasks_requirement
    ON public.evidence_collection_tasks USING btree (evidence_requirement_id);

CREATE INDEX IF NOT EXISTS idx_evidence_tasks_due
    ON public.evidence_collection_tasks USING btree (due_at);

CREATE INDEX IF NOT EXISTS idx_evidence_tasks_active
    ON public.evidence_collection_tasks USING btree (tenant_id, status, due_at)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_evidence_control_links_tenant_control
    ON public.evidence_control_links USING btree (tenant_id, control_id);

CREATE INDEX IF NOT EXISTS idx_evidence_control_links_evidence_item
    ON public.evidence_control_links USING btree (evidence_item_id);

CREATE INDEX IF NOT EXISTS idx_evidence_control_links_requirement
    ON public.evidence_control_links USING btree (evidence_requirement_id);

CREATE INDEX IF NOT EXISTS idx_evidence_control_links_framework
    ON public.evidence_control_links USING btree (framework_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_control_links_unique_requirement
    ON public.evidence_control_links USING btree (tenant_id, evidence_item_id, control_id, evidence_requirement_id)
    WHERE evidence_requirement_id IS NOT NULL AND deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_control_links_unique_control
    ON public.evidence_control_links USING btree (tenant_id, evidence_item_id, control_id)
    WHERE evidence_requirement_id IS NULL AND deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_evidence_reviews_tenant_status
    ON public.evidence_reviews USING btree (tenant_id, review_status, reviewed_at DESC);

CREATE INDEX IF NOT EXISTS idx_evidence_reviews_evidence_item
    ON public.evidence_reviews USING btree (evidence_item_id);

CREATE INDEX IF NOT EXISTS idx_evidence_reviews_package
    ON public.evidence_reviews USING btree (package_id);

CREATE INDEX IF NOT EXISTS idx_evidence_exports_tenant_status
    ON public.evidence_exports USING btree (tenant_id, status, requested_at DESC);

CREATE INDEX IF NOT EXISTS idx_evidence_exports_package
    ON public.evidence_exports USING btree (package_id);

CREATE INDEX IF NOT EXISTS idx_evidence_exports_retention
    ON public.evidence_exports USING btree (retention_until);

DROP TRIGGER IF EXISTS update_evidence_items_updated_at ON public.evidence_items;
CREATE TRIGGER update_evidence_items_updated_at
    BEFORE UPDATE ON public.evidence_items
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_evidence_packages_updated_at ON public.evidence_packages;
CREATE TRIGGER update_evidence_packages_updated_at
    BEFORE UPDATE ON public.evidence_packages
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_evidence_collection_tasks_updated_at ON public.evidence_collection_tasks;
CREATE TRIGGER update_evidence_collection_tasks_updated_at
    BEFORE UPDATE ON public.evidence_collection_tasks
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_evidence_control_links_updated_at ON public.evidence_control_links;
CREATE TRIGGER update_evidence_control_links_updated_at
    BEFORE UPDATE ON public.evidence_control_links
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_evidence_reviews_updated_at ON public.evidence_reviews;
CREATE TRIGGER update_evidence_reviews_updated_at
    BEFORE UPDATE ON public.evidence_reviews
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_evidence_exports_updated_at ON public.evidence_exports;
CREATE TRIGGER update_evidence_exports_updated_at
    BEFORE UPDATE ON public.evidence_exports
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

ALTER TABLE public.evidence_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_items FORCE ROW LEVEL SECURITY;

ALTER TABLE public.evidence_packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_packages FORCE ROW LEVEL SECURITY;

ALTER TABLE public.evidence_collection_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_collection_tasks FORCE ROW LEVEL SECURITY;

ALTER TABLE public.evidence_control_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_control_links FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_select ON public.evidence_control_links
    FOR SELECT USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_modify ON public.evidence_control_links
    FOR ALL USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY superadmin_bypass ON public.evidence_control_links
    USING (current_setting('app.is_superadmin', true) = 'true');

ALTER TABLE public.evidence_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_reviews FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_select ON public.evidence_reviews
    FOR SELECT USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_modify ON public.evidence_reviews
    FOR ALL USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY superadmin_bypass ON public.evidence_reviews
    USING (current_setting('app.is_superadmin', true) = 'true');

ALTER TABLE public.evidence_exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evidence_exports FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_select ON public.evidence_exports
    FOR SELECT USING (tenant_id = current_tenant_id());

CREATE POLICY tenant_isolation_modify ON public.evidence_exports
    FOR ALL USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY superadmin_bypass ON public.evidence_exports
    USING (current_setting('app.is_superadmin', true) = 'true');

COMMENT ON TABLE public.evidence_items IS
    'Durable compliance evidence items with provenance, validity, integrity, review, and retention metadata.';

COMMENT ON COLUMN public.evidence_items.source_resource_id IS
    'Stable source-side identifier for the collected evidence object.';

COMMENT ON COLUMN public.evidence_items.collector IS
    'Service, agent, connector, or user that collected the evidence.';

COMMENT ON COLUMN public.evidence_items.collection_method IS
    'Collection path such as api, connector, manual_upload, manual_attestation, import, or agent.';

COMMENT ON COLUMN public.evidence_items.hash_sha256 IS
    'SHA-256 hash for canonical evidence content or stored artifact integrity verification.';

COMMENT ON COLUMN public.evidence_items.storage_uri IS
    'Object storage URI or immutable reference for the evidence artifact.';

COMMENT ON COLUMN public.evidence_items.review_status IS
    'Review lifecycle state. Accepted evidence can support audit-ready control status.';

COMMENT ON TABLE public.evidence_control_links IS
    'Tenant-scoped links between evidence items, compliance controls, requirements, frameworks, and packages.';

COMMENT ON TABLE public.evidence_reviews IS
    'Review decisions for evidence items, evidence-control links, and evidence packages.';

COMMENT ON TABLE public.evidence_exports IS
    'Immutable evidence package export records with artifact integrity metadata.';
