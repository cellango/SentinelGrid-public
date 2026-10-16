-- Schema-only migration: generalized compliance coverage model fields.

ALTER TABLE public.tenant_control_status
    ADD COLUMN IF NOT EXISTS coverage_status character varying(50) DEFAULT 'not_started'::character varying NOT NULL,
    ADD COLUMN IF NOT EXISTS coverage_severity character varying(50),
    ADD COLUMN IF NOT EXISTS coverage_confidence numeric(5,4) DEFAULT 0 NOT NULL,
    ADD COLUMN IF NOT EXISTS coverage_signals jsonb DEFAULT '[]'::jsonb NOT NULL,
    ADD COLUMN IF NOT EXISTS coverage_gaps jsonb DEFAULT '[]'::jsonb NOT NULL,
    ADD COLUMN IF NOT EXISTS evidence_requirement_statuses jsonb DEFAULT '[]'::jsonb NOT NULL,
    ADD COLUMN IF NOT EXISTS last_coverage_refresh_at timestamp with time zone;

ALTER TABLE public.tenant_control_status
    DROP CONSTRAINT IF EXISTS tenant_control_status_coverage_status_check;

ALTER TABLE public.tenant_control_status
    ADD CONSTRAINT tenant_control_status_coverage_status_check
    CHECK ((coverage_status)::text = ANY (ARRAY[
        ('not_started'::character varying)::text,
        ('needs_evidence'::character varying)::text,
        ('partially_supported'::character varying)::text,
        ('ready_for_review'::character varying)::text,
        ('accepted'::character varying)::text,
        ('exception'::character varying)::text,
        ('not_applicable'::character varying)::text
    ]));

ALTER TABLE public.tenant_control_status
    DROP CONSTRAINT IF EXISTS tenant_control_status_coverage_confidence_check;

ALTER TABLE public.tenant_control_status
    ADD CONSTRAINT tenant_control_status_coverage_confidence_check
    CHECK (coverage_confidence >= 0 AND coverage_confidence <= 1);

CREATE INDEX IF NOT EXISTS idx_tenant_control_status_coverage_status
    ON public.tenant_control_status USING btree (coverage_status);

CREATE INDEX IF NOT EXISTS idx_tenant_control_status_coverage_severity
    ON public.tenant_control_status USING btree (coverage_severity);

COMMENT ON COLUMN public.tenant_control_status.coverage_status IS
    'Generalized compliance coverage status used by the multi-framework coverage engine.';

COMMENT ON COLUMN public.tenant_control_status.coverage_confidence IS
    'Confidence score from 0.0000 to 1.0000 for the current coverage status.';

