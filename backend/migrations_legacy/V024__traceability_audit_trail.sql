-- Traceability and Audit Trail System
-- Migration 024: Complete 100% traceability from detection to resolution

-- Complete incident lifecycle tracking
CREATE TABLE IF NOT EXISTS incident_lifecycle (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    detection_event_id TEXT,  -- Event ID from OpenSearch detection index
    rule_id UUID REFERENCES detection_rules(id),
    rule_version TEXT,
    alert_raw_payload JSONB,  -- Original alert from OpenSearch for forensics
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Detailed timeline for every action
CREATE TABLE IF NOT EXISTS incident_timeline (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type TEXT NOT NULL,  -- 'detection', 'status_change', 'playbook_executed', 'action_taken', 'comment_added', 'assignment_changed'
    actor_type TEXT NOT NULL,  -- 'system', 'user', 'playbook', 'api'
    actor_id TEXT,  -- User ID or system component
    nist_phase TEXT,  -- Current NIST phase at time of event
    nist_status TEXT,  -- Current NIST status at time of event
    action TEXT NOT NULL,  -- 'detected', 'triaged', 'contained', 'disabled_user', etc.
    description TEXT,
    metadata JSONB,  -- Additional context (IPs, users affected, etc.)
    playbook_execution_id UUID,  -- Link to playbook if action from playbook
    related_entity_type TEXT,  -- 'alert', 'user', 'host', 'observable'
    related_entity_id TEXT,
    before_state JSONB,  -- State before action
    after_state JSONB,  -- State after action
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT true,
    error_message TEXT
);

-- Playbook execution audit trail
CREATE TABLE IF NOT EXISTS playbook_execution_audit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id UUID NOT NULL REFERENCES playbook_executions(id) ON DELETE CASCADE,
    incident_id UUID NOT NULL REFERENCES incidents(id),
    playbook_id UUID NOT NULL REFERENCES playbooks(id),
    playbook_version TEXT,
    node_id TEXT,  -- Which playbook node executed
    node_type TEXT,  -- 'action', 'decision', 'manual', etc.
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL,  -- 'pending', 'running', 'success', 'failed', 'skipped'
    input_data JSONB,  -- Input parameters to this node
    output_data JSONB,  -- Output/result from this node
    error_message TEXT,
    execution_order INTEGER,  -- Sequence in playbook
    created_by TEXT
);

-- Actions taken tracking (for evidence and compliance)
CREATE TABLE IF NOT EXISTS incident_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,  -- 'disable_user', 'quarantine_host', 'block_ip', 'password_reset', etc.
    target_entity_type TEXT,  -- 'user', 'host', 'ip', 'domain', 'file_hash'
    target_entity_id TEXT,
    target_entity_name TEXT,  -- Human-readable name
    action_taken_by TEXT NOT NULL,  -- User ID or 'system'
    action_source TEXT NOT NULL,  -- 'manual', 'playbook', 'api'
    playbook_execution_id UUID,  -- If from playbook
    nist_phase TEXT,  -- Phase when action taken
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    before_state JSONB,  -- State before action
    after_state JSONB,  -- State after action
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    rollback_possible BOOLEAN DEFAULT false,
    rollback_procedure TEXT,  -- How to undo this action
    evidence_collected JSONB  -- Forensic evidence from this action
);

-- Observable/IOC tracking with provenance
CREATE TABLE IF NOT EXISTS incident_observables (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    observable_type TEXT NOT NULL,  -- 'ip', 'domain', 'file_hash', 'email', 'url', 'user', 'host'
    observable_value TEXT NOT NULL,
    source TEXT NOT NULL,  -- Where it came from: 'detection_rule', 'playbook_extraction', 'manual_entry'
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    extracted_by TEXT,  -- User or system component
    confidence REAL,  -- 0.0-1.0
    is_malicious BOOLEAN,
    threat_intel_enrichment JSONB,  -- CTI data
    tags TEXT[],
    first_seen TIMESTAMPTZ,
    last_seen TIMESTAMPTZ
);

-- Evidence chain of custody
CREATE TABLE IF NOT EXISTS incident_evidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL,  -- 'log_snapshot', 'file', 'memory_dump', 'screenshot', 'pcap'
    evidence_location TEXT NOT NULL,  -- S3 path, file path, etc.
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    collected_by TEXT NOT NULL,
    collection_method TEXT,  -- 'automated', 'manual', 'playbook'
    hash_sha256 TEXT,  -- File integrity
    size_bytes BIGINT,
    metadata JSONB,
    chain_of_custody JSONB  -- Array of custody transfers
);

-- Create indexes for performance
CREATE INDEX idx_lifecycle_incident ON incident_lifecycle(incident_id);
CREATE INDEX idx_lifecycle_rule ON incident_lifecycle(rule_id);
CREATE INDEX idx_timeline_incident ON incident_timeline(incident_id, timestamp DESC);
CREATE INDEX idx_timeline_actor ON incident_timeline(actor_id, timestamp DESC);
CREATE INDEX idx_timeline_type ON incident_timeline(incident_id, event_type);
CREATE INDEX idx_pb_audit_execution ON playbook_execution_audit(execution_id, execution_order);
CREATE INDEX idx_pb_audit_incident ON playbook_execution_audit(incident_id, started_at DESC);
CREATE INDEX idx_actions_incident ON incident_actions(incident_id, timestamp DESC);
CREATE INDEX idx_actions_target ON incident_actions(target_entity_type, target_entity_id);
CREATE INDEX idx_observables_incident ON incident_observables(incident_id);
CREATE INDEX idx_observables_value ON incident_observables(observable_type, observable_value);
CREATE INDEX idx_evidence_incident ON incident_evidence(incident_id, collected_at DESC);

-- Comments for documentation
COMMENT ON TABLE incident_lifecycle IS 'Complete lineage from detection rule to incident';
COMMENT ON TABLE incident_timeline IS 'Microsecond-precision timeline of all actions';
COMMENT ON TABLE playbook_execution_audit IS 'Detailed audit of every playbook node execution';
COMMENT ON TABLE incident_actions IS 'All actions taken during incident response';
COMMENT ON TABLE incident_observables IS 'IOCs with provenance tracking';
COMMENT ON TABLE incident_evidence IS 'Forensic evidence with chain of custody';

COMMENT ON COLUMN incident_lifecycle.detection_event_id IS 'Links to detection event in OpenSearch';
COMMENT ON COLUMN incident_timeline.before_state IS 'State snapshot before action for forensics';
COMMENT ON COLUMN incident_timeline.after_state IS 'State snapshot after action for forensics';
COMMENT ON COLUMN incident_actions.rollback_procedure IS 'Instructions to reverse this action';
COMMENT ON COLUMN incident_observables.source IS 'Provenance: where did this IOC come from?';
COMMENT ON COLUMN incident_evidence.chain_of_custody IS 'Who handled evidence and when';

