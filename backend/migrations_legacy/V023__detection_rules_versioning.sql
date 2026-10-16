-- Detection Rules Versioning and Management
-- Migration 023: Detection rules with semantic versioning and tenant deployment tracking

-- Detection rules catalog with versioning
CREATE TABLE IF NOT EXISTS detection_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_key TEXT NOT NULL UNIQUE,  -- 'SG-DET-001', 'SG-DET-002', etc.
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,  -- 'identity', 'email', 'endpoint', 'cloud', 'network', 'device'
    current_version TEXT NOT NULL,  -- '1.0.0', '1.1.0', '2.0.0'
    is_builtin BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Version history with full rule definition
CREATE TABLE IF NOT EXISTS detection_rule_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id UUID NOT NULL REFERENCES detection_rules(id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    index_pattern TEXT NOT NULL,  -- 'sg-{tenant}-auth-*', etc.
    query JSONB NOT NULL,  -- OpenSearch query DSL
    trigger_condition JSONB NOT NULL,  -- Threshold, frequency, aggregations, etc.
    severity TEXT NOT NULL,  -- 'critical', 'high', 'medium', 'low'
    action_config JSONB NOT NULL,  -- Webhook config, throttle, destinations
    metadata JSONB,  -- MITRE, NIST mappings, tags, additional context
    changelog TEXT,  -- What changed in this version
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    UNIQUE(rule_id, version)
);

-- Track deployed monitors per tenant
CREATE TABLE IF NOT EXISTS tenant_detection_monitors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    rule_id UUID NOT NULL REFERENCES detection_rules(id),
    rule_version TEXT NOT NULL,
    opensearch_monitor_id TEXT NOT NULL,  -- ID from OpenSearch Alerting API
    opensearch_destination_id TEXT,  -- Webhook destination ID
    is_enabled BOOLEAN DEFAULT true,
    custom_config JSONB,  -- Tenant-specific overrides (thresholds, etc.)
    deployed_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, rule_id)
);

-- Detection rule execution history (audit trail)
CREATE TABLE IF NOT EXISTS detection_rule_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    rule_id UUID NOT NULL REFERENCES detection_rules(id),
    rule_version TEXT NOT NULL,
    fired_at TIMESTAMPTZ NOT NULL,
    match_count INTEGER NOT NULL,
    detection_event_ids TEXT[],  -- Array of detection event IDs created
    incident_ids UUID[],  -- Array of incident IDs created
    execution_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Detection to playbook mapping
CREATE TABLE IF NOT EXISTS detection_playbook_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    rule_id UUID REFERENCES detection_rules(id) ON DELETE CASCADE,
    alert_type TEXT NOT NULL,  -- e.g., 'suspicious_login', 'phishing_user_report'
    playbook_id UUID REFERENCES playbooks(id) ON DELETE SET NULL,
    playbook_key TEXT,  -- e.g., 'PLAYBOOK_ACCOUNT_TAKEOVER' (for built-in playbooks)
    auto_execute BOOLEAN DEFAULT false,  -- Auto-execute playbook when alert fires
    requires_approval BOOLEAN DEFAULT true,  -- Require approval before execution
    severity_threshold TEXT,  -- Only trigger for 'high', 'critical', etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, rule_id),
    UNIQUE(tenant_id, alert_type)  -- One mapping per alert type per tenant
);

-- Create indexes for performance
CREATE INDEX idx_rule_executions_tenant ON detection_rule_executions(tenant_id, fired_at DESC);
CREATE INDEX idx_rule_executions_rule ON detection_rule_executions(rule_id, fired_at DESC);
CREATE INDEX idx_tenant_monitors_tenant ON tenant_detection_monitors(tenant_id);
CREATE INDEX idx_tenant_monitors_rule ON tenant_detection_monitors(rule_id);
CREATE INDEX idx_playbook_mappings_tenant ON detection_playbook_mappings(tenant_id);
CREATE INDEX idx_playbook_mappings_alert_type ON detection_playbook_mappings(alert_type);

-- Comments for documentation
COMMENT ON TABLE detection_rules IS 'Catalog of all detection rules with semantic versioning';
COMMENT ON TABLE detection_rule_versions IS 'Complete version history of detection rules';
COMMENT ON TABLE tenant_detection_monitors IS 'Tracks which monitors are deployed to which tenants';
COMMENT ON TABLE detection_rule_executions IS 'Audit trail of detection rule firings';
COMMENT ON TABLE detection_playbook_mappings IS 'Maps alert types to playbooks for automated response';

COMMENT ON COLUMN detection_rules.rule_key IS 'Unique identifier like SG-DET-001';
COMMENT ON COLUMN detection_rule_versions.query IS 'OpenSearch Query DSL as JSON';
COMMENT ON COLUMN detection_rule_versions.trigger_condition IS 'Conditions to trigger alert (threshold, aggregations)';
COMMENT ON COLUMN tenant_detection_monitors.opensearch_monitor_id IS 'Monitor ID from OpenSearch Alerting API';
COMMENT ON COLUMN detection_playbook_mappings.auto_execute IS 'If true, playbook runs automatically without approval';

