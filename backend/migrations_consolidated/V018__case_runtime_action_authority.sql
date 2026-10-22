-- Paired action-authority storage; application records, not an engine scheduler.
CREATE SCHEMA case_runtime;
SET search_path = case_runtime, pg_catalog;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';

CREATE TABLE case_runtime.cases (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	revision INTEGER DEFAULT 1 NOT NULL, 
	plan_revision INTEGER DEFAULT 1 NOT NULL, 
	policy_version TEXT NOT NULL, 
	status TEXT DEFAULT 'open' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_cases_tenant_id UNIQUE (tenant_id, id), 
	CONSTRAINT ck_cases_revision CHECK (revision > 0 AND plan_revision > 0)
)

;

CREATE TABLE case_runtime.outbox_events (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	aggregate_id UUID NOT NULL, 
	event_type TEXT NOT NULL, 
	payload JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
)

;
CREATE INDEX ix_action_outbox_tenant_created ON case_runtime.outbox_events (tenant_id, created_at);

CREATE TABLE case_runtime.resource_fences (
	tenant_id UUID NOT NULL, 
	resource_key TEXT NOT NULL, 
	generation INTEGER NOT NULL, 
	PRIMARY KEY (tenant_id, resource_key), 
	CONSTRAINT ck_resource_fence_generation CHECK (generation > 0)
)

;

CREATE TABLE case_runtime.action_proposals (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	action_id UUID NOT NULL, 
	proposal_revision INTEGER NOT NULL, 
	case_revision INTEGER NOT NULL, 
	plan_revision INTEGER NOT NULL, 
	policy_version TEXT NOT NULL, 
	tool_id TEXT NOT NULL, 
	tool_version TEXT NOT NULL, 
	proposed_by UUID NOT NULL, 
	request_key UUID NOT NULL, 
	request_hash TEXT NOT NULL, 
	proposal_hash TEXT NOT NULL, 
	canonical_payload TEXT NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id, case_id) REFERENCES case_runtime.cases (tenant_id, id), 
	CONSTRAINT uq_proposal_tenant_id UNIQUE (tenant_id, id), 
	CONSTRAINT uq_proposal_action_binding UNIQUE (tenant_id, id, proposal_hash, action_id), 
	CONSTRAINT ck_proposal_payload_bound CHECK (octet_length(canonical_payload) <= 32768), 
	CONSTRAINT uq_proposal_hash_binding UNIQUE (tenant_id, id, proposal_hash), 
	CONSTRAINT uq_action_proposal_revision UNIQUE (tenant_id, action_id, proposal_revision), 
	CONSTRAINT uq_proposal_request UNIQUE (tenant_id, case_id, request_key), 
	CONSTRAINT ck_proposal_revision CHECK (proposal_revision > 0 AND case_revision > 0 AND plan_revision > 0), 
	CONSTRAINT ck_proposal_hashes CHECK (proposal_hash ~ '^[a-f0-9]{64}$' AND request_hash ~ '^[a-f0-9]{64}$')
)

;

CREATE TABLE case_runtime.case_access_grants (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	subject_id UUID NOT NULL, 
	permission TEXT NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id, case_id) REFERENCES case_runtime.cases (tenant_id, id), 
	CONSTRAINT uq_case_grant UNIQUE (tenant_id, case_id, subject_id, permission), 
	CONSTRAINT ck_case_grant_permission CHECK (permission IN ('propose','approve','execute','verify','read'))
)

;

CREATE TABLE case_runtime.approval_decisions (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	proposal_id UUID NOT NULL, 
	proposal_hash TEXT NOT NULL, 
	sequence INTEGER NOT NULL, 
	decided_by UUID NOT NULL, 
	decision TEXT NOT NULL, 
	reason TEXT NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id, proposal_id, proposal_hash) REFERENCES case_runtime.action_proposals (tenant_id, id, proposal_hash), 
	CONSTRAINT uq_approval_sequence UNIQUE (tenant_id, proposal_id, sequence), 
	CONSTRAINT uq_decision_hash_binding UNIQUE (tenant_id, id, proposal_id, proposal_hash), 
	CONSTRAINT ck_approval_decision CHECK (decision IN ('approve','reject','revoke') AND sequence > 0)
)

;

CREATE TABLE case_runtime.approval_requests (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	proposal_id UUID NOT NULL, 
	proposal_hash TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id, proposal_id, proposal_hash) REFERENCES case_runtime.action_proposals (tenant_id, id, proposal_hash), 
	CONSTRAINT uq_approval_request_proposal UNIQUE (tenant_id, proposal_id)
)

;

CREATE TABLE case_runtime.policy_decisions (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	proposal_id UUID NOT NULL, 
	actor_id UUID NOT NULL, 
	policy_version TEXT NOT NULL, 
	proposal_hash TEXT NOT NULL, 
	decision TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id, proposal_id, proposal_hash) REFERENCES case_runtime.action_proposals (tenant_id, id, proposal_hash), 
	CONSTRAINT ck_policy_decision CHECK (decision IN ('allow','deny','approval_required'))
)

;

CREATE TABLE case_runtime.action_claims (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	proposal_id UUID NOT NULL, 
	action_id UUID NOT NULL, 
	actor_id UUID NOT NULL, 
	approval_id UUID NOT NULL, 
	proposal_hash TEXT NOT NULL, 
	idempotency_key TEXT NOT NULL, 
	resource_fences JSONB NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id, proposal_id, proposal_hash, action_id) REFERENCES case_runtime.action_proposals (tenant_id, id, proposal_hash, action_id), 
	CONSTRAINT uq_claim_tenant_id UNIQUE (tenant_id, id), 
	FOREIGN KEY(tenant_id, approval_id, proposal_id, proposal_hash) REFERENCES case_runtime.approval_decisions (tenant_id, id, proposal_id, proposal_hash), 
	CONSTRAINT uq_action_claim UNIQUE (tenant_id, action_id), 
	CONSTRAINT uq_effect_key UNIQUE (tenant_id, idempotency_key)
)

;

CREATE TABLE case_runtime.action_attempts (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	claim_id UUID NOT NULL, 
	attempt_number INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id, claim_id) REFERENCES case_runtime.action_claims (tenant_id, id), 
	CONSTRAINT uq_action_attempt UNIQUE (tenant_id, claim_id, attempt_number), 
	CONSTRAINT ck_attempt_number CHECK (attempt_number > 0)
)

;

CREATE TABLE case_runtime.action_receipts (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	claim_id UUID NOT NULL, 
	outcome TEXT NOT NULL, 
	provider_request_id TEXT, 
	evidence_reference TEXT, 
	simulated BOOLEAN DEFAULT false NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id, claim_id) REFERENCES case_runtime.action_claims (tenant_id, id), 
	CONSTRAINT uq_action_receipt UNIQUE (tenant_id, claim_id), 
	CONSTRAINT ck_receipt_outcome CHECK (outcome IN ('executed','failed','ambiguous','unsupported','cancelled'))
)

;

CREATE TABLE case_runtime.action_verifications (
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	claim_id UUID NOT NULL, 
	verified_by UUID NOT NULL, 
	outcome TEXT NOT NULL, 
	evidence_reference TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id, claim_id) REFERENCES case_runtime.action_claims (tenant_id, id), 
	CONSTRAINT ck_verification_outcome CHECK (outcome IN ('passed','failed','inconclusive'))
)

;
CREATE FUNCTION case_runtime.current_tenant_id() RETURNS uuid
LANGUAGE plpgsql STABLE SECURITY INVOKER SET search_path = pg_catalog AS $$
BEGIN
 RETURN NULLIF(current_setting('app.current_tenant_id',true),'')::uuid;
EXCEPTION WHEN invalid_text_representation THEN RETURN NULL;
END; $$;

CREATE FUNCTION case_runtime.immutable_action_record() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog AS $$
BEGIN RAISE EXCEPTION 'Immutable action record' USING ERRCODE='23514'; END; $$;

ALTER TABLE case_runtime.cases ENABLE ROW LEVEL SECURITY;

ALTER TABLE case_runtime.cases FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_access ON case_runtime.cases USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

CREATE POLICY tenant_guard ON case_runtime.cases AS RESTRICTIVE USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

REVOKE ALL ON case_runtime.cases FROM PUBLIC;

ALTER TABLE case_runtime.outbox_events ENABLE ROW LEVEL SECURITY;

ALTER TABLE case_runtime.outbox_events FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_access ON case_runtime.outbox_events USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

CREATE POLICY tenant_guard ON case_runtime.outbox_events AS RESTRICTIVE USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

REVOKE ALL ON case_runtime.outbox_events FROM PUBLIC;

CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON case_runtime.outbox_events FOR EACH ROW EXECUTE FUNCTION case_runtime.immutable_action_record();

ALTER TABLE case_runtime.resource_fences ENABLE ROW LEVEL SECURITY;

ALTER TABLE case_runtime.resource_fences FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_access ON case_runtime.resource_fences USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

CREATE POLICY tenant_guard ON case_runtime.resource_fences AS RESTRICTIVE USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

REVOKE ALL ON case_runtime.resource_fences FROM PUBLIC;

ALTER TABLE case_runtime.action_proposals ENABLE ROW LEVEL SECURITY;

ALTER TABLE case_runtime.action_proposals FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_access ON case_runtime.action_proposals USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

CREATE POLICY tenant_guard ON case_runtime.action_proposals AS RESTRICTIVE USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

REVOKE ALL ON case_runtime.action_proposals FROM PUBLIC;

CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON case_runtime.action_proposals FOR EACH ROW EXECUTE FUNCTION case_runtime.immutable_action_record();

ALTER TABLE case_runtime.case_access_grants ENABLE ROW LEVEL SECURITY;

ALTER TABLE case_runtime.case_access_grants FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_access ON case_runtime.case_access_grants USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

CREATE POLICY tenant_guard ON case_runtime.case_access_grants AS RESTRICTIVE USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

REVOKE ALL ON case_runtime.case_access_grants FROM PUBLIC;

ALTER TABLE case_runtime.approval_decisions ENABLE ROW LEVEL SECURITY;

ALTER TABLE case_runtime.approval_decisions FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_access ON case_runtime.approval_decisions USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

CREATE POLICY tenant_guard ON case_runtime.approval_decisions AS RESTRICTIVE USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

REVOKE ALL ON case_runtime.approval_decisions FROM PUBLIC;

CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON case_runtime.approval_decisions FOR EACH ROW EXECUTE FUNCTION case_runtime.immutable_action_record();

ALTER TABLE case_runtime.approval_requests ENABLE ROW LEVEL SECURITY;

ALTER TABLE case_runtime.approval_requests FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_access ON case_runtime.approval_requests USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

CREATE POLICY tenant_guard ON case_runtime.approval_requests AS RESTRICTIVE USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

REVOKE ALL ON case_runtime.approval_requests FROM PUBLIC;

CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON case_runtime.approval_requests FOR EACH ROW EXECUTE FUNCTION case_runtime.immutable_action_record();

ALTER TABLE case_runtime.policy_decisions ENABLE ROW LEVEL SECURITY;

ALTER TABLE case_runtime.policy_decisions FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_access ON case_runtime.policy_decisions USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

CREATE POLICY tenant_guard ON case_runtime.policy_decisions AS RESTRICTIVE USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

REVOKE ALL ON case_runtime.policy_decisions FROM PUBLIC;

CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON case_runtime.policy_decisions FOR EACH ROW EXECUTE FUNCTION case_runtime.immutable_action_record();

ALTER TABLE case_runtime.action_claims ENABLE ROW LEVEL SECURITY;

ALTER TABLE case_runtime.action_claims FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_access ON case_runtime.action_claims USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

CREATE POLICY tenant_guard ON case_runtime.action_claims AS RESTRICTIVE USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

REVOKE ALL ON case_runtime.action_claims FROM PUBLIC;

CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON case_runtime.action_claims FOR EACH ROW EXECUTE FUNCTION case_runtime.immutable_action_record();

ALTER TABLE case_runtime.action_attempts ENABLE ROW LEVEL SECURITY;

ALTER TABLE case_runtime.action_attempts FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_access ON case_runtime.action_attempts USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

CREATE POLICY tenant_guard ON case_runtime.action_attempts AS RESTRICTIVE USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

REVOKE ALL ON case_runtime.action_attempts FROM PUBLIC;

CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON case_runtime.action_attempts FOR EACH ROW EXECUTE FUNCTION case_runtime.immutable_action_record();

ALTER TABLE case_runtime.action_receipts ENABLE ROW LEVEL SECURITY;

ALTER TABLE case_runtime.action_receipts FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_access ON case_runtime.action_receipts USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

CREATE POLICY tenant_guard ON case_runtime.action_receipts AS RESTRICTIVE USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

REVOKE ALL ON case_runtime.action_receipts FROM PUBLIC;

CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON case_runtime.action_receipts FOR EACH ROW EXECUTE FUNCTION case_runtime.immutable_action_record();

ALTER TABLE case_runtime.action_verifications ENABLE ROW LEVEL SECURITY;

ALTER TABLE case_runtime.action_verifications FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_access ON case_runtime.action_verifications USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

CREATE POLICY tenant_guard ON case_runtime.action_verifications AS RESTRICTIVE USING (tenant_id=case_runtime.current_tenant_id()) WITH CHECK (tenant_id=case_runtime.current_tenant_id());

REVOKE ALL ON case_runtime.action_verifications FROM PUBLIC;

CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON case_runtime.action_verifications FOR EACH ROW EXECUTE FUNCTION case_runtime.immutable_action_record();

REVOKE ALL ON SCHEMA case_runtime FROM PUBLIC;

-- Runtime grants are a separate least-privilege infrastructure step; no role or existing data is adopted here.
