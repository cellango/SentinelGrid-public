-- Storage only. No roles, application grants, writer, scheduler or provider activation.
SET search_path = case_runtime, pg_catalog;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

CREATE TABLE case_runtime.evidence_references (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	source_type TEXT NOT NULL,
	source_locator TEXT NOT NULL,
	source_version TEXT NOT NULL,
	content_sha256 TEXT,
	digest_unavailable_reason TEXT,
	observed_at TIMESTAMP WITH TIME ZONE NOT NULL,
	collected_at TIMESTAMP WITH TIME ZONE NOT NULL,
	retain_until TIMESTAMP WITH TIME ZONE NOT NULL,
	access_class TEXT NOT NULL,
	custody_reference TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_evidence_tenant_id UNIQUE (tenant_id, id),
	CONSTRAINT ck_evidence_non_nil CHECK (id <> '00000000-0000-0000-0000-000000000000'::uuid AND tenant_id <> '00000000-0000-0000-0000-000000000000'::uuid),
	CONSTRAINT ck_evidence_digest_or_reason CHECK ((content_sha256 IS NOT NULL AND content_sha256 ~ '^[a-f0-9]{64}$' AND digest_unavailable_reason IS NULL) OR (content_sha256 IS NULL AND octet_length(digest_unavailable_reason) BETWEEN 1 AND 512)),
	CONSTRAINT ck_evidence_digest_presence CHECK (content_sha256 IS NOT NULL OR digest_unavailable_reason IS NOT NULL),
	CONSTRAINT ck_evidence_times CHECK (observed_at <= collected_at AND retain_until > collected_at),
	CONSTRAINT ck_provenance_source_type_bound CHECK (octet_length(source_type) BETWEEN 1 AND 80),
	CONSTRAINT ck_provenance_source_locator_bound CHECK (octet_length(source_locator) BETWEEN 1 AND 2048),
	CONSTRAINT ck_provenance_source_version_bound CHECK (octet_length(source_version) BETWEEN 1 AND 256),
	CONSTRAINT ck_provenance_access_class_bound CHECK (octet_length(access_class) BETWEEN 1 AND 80),
	CONSTRAINT ck_provenance_custody_reference_bound CHECK (octet_length(custody_reference) BETWEEN 1 AND 2048)
);
ALTER TABLE case_runtime.evidence_references ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_runtime.evidence_references FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_access ON case_runtime.evidence_references USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());
CREATE POLICY tenant_guard ON case_runtime.evidence_references AS RESTRICTIVE USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());
REVOKE ALL ON case_runtime.evidence_references FROM PUBLIC;
CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON case_runtime.evidence_references FOR EACH ROW EXECUTE FUNCTION case_runtime.immutable_action_record();

CREATE TABLE case_runtime.run_manifests (
	id UUID NOT NULL,
	tenant_id UUID NOT NULL,
	case_id UUID NOT NULL,
	request_key UUID NOT NULL,
	initiated_by UUID NOT NULL,
	mode TEXT NOT NULL,
	schema_version TEXT NOT NULL,
	trigger_reference TEXT NOT NULL,
	source_content_reference TEXT NOT NULL,
	playbook_version TEXT NOT NULL,
	selection_version TEXT NOT NULL,
	skill_version TEXT NOT NULL,
	model_version TEXT NOT NULL,
	prompt_version TEXT NOT NULL,
	toolset_version TEXT NOT NULL,
	policy_version TEXT NOT NULL,
	runtime_version TEXT NOT NULL,
	payload TEXT NOT NULL,
	payload_sha256 TEXT NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id, case_id) REFERENCES case_runtime.cases (tenant_id, id),
	CONSTRAINT uq_manifest_tenant_case_run UNIQUE (tenant_id, case_id, id),
	CONSTRAINT uq_manifest_request UNIQUE (tenant_id, case_id, request_key),
	CONSTRAINT ck_manifest_non_nil CHECK (id <> '00000000-0000-0000-0000-000000000000'::uuid AND request_key <> '00000000-0000-0000-0000-000000000000'::uuid AND initiated_by <> '00000000-0000-0000-0000-000000000000'::uuid),
	CONSTRAINT ck_manifest_mode CHECK (mode IN ('recommendation_only','synthetic','live')),
	CONSTRAINT ck_manifest_schema CHECK (schema_version = 'run-manifest-v1'),
	CONSTRAINT ck_manifest_payload CHECK (octet_length(payload) BETWEEN 2 AND 262144 AND jsonb_typeof(payload::jsonb) = 'object'),
	CONSTRAINT ck_manifest_payload_digest CHECK (payload_sha256 = encode(sha256(convert_to(payload,'UTF8')),'hex')),
	CONSTRAINT ck_manifest_evidence_ids CHECK (payload::jsonb ? 'evidence_ids' AND jsonb_typeof(payload::jsonb->'evidence_ids') = 'array' AND jsonb_array_length(payload::jsonb->'evidence_ids') <= 256),
	CONSTRAINT ck_provenance_playbook_version_bound CHECK (octet_length(playbook_version) BETWEEN 1 AND 256),
	CONSTRAINT ck_provenance_selection_version_bound CHECK (octet_length(selection_version) BETWEEN 1 AND 256),
	CONSTRAINT ck_provenance_skill_version_bound CHECK (octet_length(skill_version) BETWEEN 1 AND 256),
	CONSTRAINT ck_provenance_model_version_bound CHECK (octet_length(model_version) BETWEEN 1 AND 256),
	CONSTRAINT ck_provenance_prompt_version_bound CHECK (octet_length(prompt_version) BETWEEN 1 AND 256),
	CONSTRAINT ck_provenance_toolset_version_bound CHECK (octet_length(toolset_version) BETWEEN 1 AND 256),
	CONSTRAINT ck_provenance_policy_version_bound CHECK (octet_length(policy_version) BETWEEN 1 AND 256),
	CONSTRAINT ck_provenance_runtime_version_bound CHECK (octet_length(runtime_version) BETWEEN 1 AND 256),
	CONSTRAINT ck_provenance_trigger_reference_bound CHECK (octet_length(trigger_reference) BETWEEN 1 AND 2048),
	CONSTRAINT ck_provenance_source_content_reference_bound CHECK (octet_length(source_content_reference) BETWEEN 1 AND 2048)
);
ALTER TABLE case_runtime.run_manifests ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_runtime.run_manifests FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_access ON case_runtime.run_manifests USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());
CREATE POLICY tenant_guard ON case_runtime.run_manifests AS RESTRICTIVE USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());
REVOKE ALL ON case_runtime.run_manifests FROM PUBLIC;
CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON case_runtime.run_manifests FOR EACH ROW EXECUTE FUNCTION case_runtime.immutable_action_record();

CREATE TABLE case_runtime.case_evidence_links (
	tenant_id UUID NOT NULL,
	case_id UUID NOT NULL,
	evidence_id UUID NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (tenant_id, case_id, evidence_id),
	FOREIGN KEY(tenant_id, case_id) REFERENCES case_runtime.cases (tenant_id, id),
	FOREIGN KEY(tenant_id, evidence_id) REFERENCES case_runtime.evidence_references (tenant_id, id)
);
ALTER TABLE case_runtime.case_evidence_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_runtime.case_evidence_links FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_access ON case_runtime.case_evidence_links USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());
CREATE POLICY tenant_guard ON case_runtime.case_evidence_links AS RESTRICTIVE USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());
REVOKE ALL ON case_runtime.case_evidence_links FROM PUBLIC;
CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON case_runtime.case_evidence_links FOR EACH ROW EXECUTE FUNCTION case_runtime.immutable_action_record();

CREATE TABLE case_runtime.run_evidence_links (
	tenant_id UUID NOT NULL,
	case_id UUID NOT NULL,
	run_id UUID NOT NULL,
	evidence_id UUID NOT NULL,
	PRIMARY KEY (tenant_id, case_id, run_id, evidence_id),
	FOREIGN KEY(tenant_id, case_id, run_id) REFERENCES case_runtime.run_manifests (tenant_id, case_id, id),
	FOREIGN KEY(tenant_id, case_id, evidence_id) REFERENCES case_runtime.case_evidence_links (tenant_id, case_id, evidence_id)
);
ALTER TABLE case_runtime.run_evidence_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_runtime.run_evidence_links FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_access ON case_runtime.run_evidence_links USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());
CREATE POLICY tenant_guard ON case_runtime.run_evidence_links AS RESTRICTIVE USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());
REVOKE ALL ON case_runtime.run_evidence_links FROM PUBLIC;
CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON case_runtime.run_evidence_links FOR EACH ROW EXECUTE FUNCTION case_runtime.immutable_action_record();

-- Exact evidence set is committed with its manifest; links cannot extend it later.
CREATE FUNCTION case_runtime.check_manifest_evidence() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog AS $$
DECLARE run_uuid uuid; declared jsonb; actual jsonb;
BEGIN
 IF TG_TABLE_NAME = 'run_manifests' THEN run_uuid := NEW.id;
 ELSE run_uuid := NEW.run_id; END IF;
 SELECT payload::jsonb->'evidence_ids' INTO declared FROM case_runtime.run_manifests
 WHERE tenant_id=NEW.tenant_id AND case_id=NEW.case_id AND id=run_uuid;
 SELECT COALESCE(jsonb_agg(evidence_id::text ORDER BY evidence_id::text),'[]'::jsonb)
 INTO actual FROM case_runtime.run_evidence_links
 WHERE tenant_id=NEW.tenant_id AND case_id=NEW.case_id AND run_id=run_uuid;
 IF declared IS NULL OR actual IS DISTINCT FROM
   (SELECT COALESCE(jsonb_agg(value ORDER BY value),'[]'::jsonb) FROM jsonb_array_elements(declared))
 THEN RAISE EXCEPTION 'Manifest evidence set mismatch' USING ERRCODE='23514'; END IF;
 RETURN NULL;
END; $$;
REVOKE ALL ON FUNCTION case_runtime.check_manifest_evidence() FROM PUBLIC;
CREATE CONSTRAINT TRIGGER manifest_evidence_complete AFTER INSERT ON case_runtime.run_manifests
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION case_runtime.check_manifest_evidence();
CREATE CONSTRAINT TRIGGER manifest_evidence_complete AFTER INSERT ON case_runtime.run_evidence_links
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION case_runtime.check_manifest_evidence();
