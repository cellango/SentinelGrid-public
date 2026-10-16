-- Schema-only migration: compliance control evidence requirements.
-- Data remains seeded outside Flyway per the migrations policy.

CREATE TABLE IF NOT EXISTS public.control_evidence_requirements (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    control_id uuid NOT NULL,
    requirement_key character varying(120) NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    evidence_type character varying(100),
    source_system character varying(120),
    is_required boolean DEFAULT true NOT NULL,
    collection_frequency character varying(80),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

ALTER TABLE ONLY public.control_evidence_requirements
    ADD CONSTRAINT control_evidence_requirements_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.control_evidence_requirements
    ADD CONSTRAINT control_evidence_requirements_control_key UNIQUE (control_id, requirement_key);

ALTER TABLE ONLY public.control_evidence_requirements
    ADD CONSTRAINT control_evidence_requirements_control_id_fkey
    FOREIGN KEY (control_id) REFERENCES public.compliance_controls(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_control_evidence_requirements_control
    ON public.control_evidence_requirements USING btree (control_id);

CREATE INDEX IF NOT EXISTS idx_control_evidence_requirements_type
    ON public.control_evidence_requirements USING btree (evidence_type);

CREATE INDEX IF NOT EXISTS idx_control_evidence_requirements_source
    ON public.control_evidence_requirements USING btree (source_system);

COMMENT ON TABLE public.control_evidence_requirements IS
    'Canonical evidence requirements for compliance controls. Seeded outside Flyway.';

