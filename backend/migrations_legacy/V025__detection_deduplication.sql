-- Detection Deduplication and Suppression
-- Migration 025: Prevents duplicate incidents and alert fatigue

-- Deduplication tracking - identifies duplicate detection events
CREATE TABLE IF NOT EXISTS detection_deduplication (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    rule_id UUID NOT NULL REFERENCES detection_rules(id),
    dedup_key TEXT NOT NULL,  -- Hash of key fields that define uniqueness
    dedup_fields JSONB NOT NULL,  -- Fields used for deduplication (user_id, host_id, etc.)
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    incident_id UUID REFERENCES incidents(id),  -- First incident created for this pattern
    last_detection_event_id TEXT,  -- Most recent detection event ID
    status TEXT NOT NULL DEFAULT 'active',  -- 'active', 'suppressed', 'resolved'
    suppressed_until TIMESTAMPTZ,  -- Temporary suppression end time
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Suppression rules - configure when to suppress alerts
CREATE TABLE IF NOT EXISTS detection_suppression_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    rule_id UUID REFERENCES detection_rules(id),  -- NULL = applies to all rules
    name TEXT NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT true,
    
    -- Suppression criteria
    alert_types TEXT[],  -- Which alert types to suppress
    time_window_minutes INTEGER NOT NULL DEFAULT 60,  -- Dedup window
    max_occurrences INTEGER NOT NULL DEFAULT 1,  -- Max incidents per window
    
    -- Grouping fields for deduplication
    group_by_fields TEXT[] NOT NULL,  -- ['user.id', 'source.ip', 'host.name', etc.]
    
    -- Escalation policy
    escalate_after_count INTEGER,  -- Create incident after N occurrences
    escalate_if_severity TEXT[],  -- Escalate if severity changes to these
    
    -- Time-based suppression
    suppress_during_maintenance BOOLEAN DEFAULT false,
    maintenance_schedule JSONB,  -- Cron-like schedule
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT
);

-- Suppression events log - tracks when alerts were suppressed
CREATE TABLE IF NOT EXISTS detection_suppression_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    dedup_id UUID REFERENCES detection_deduplication(id),
    suppression_rule_id UUID REFERENCES detection_suppression_rules(id),
    detection_event_id TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    suppressed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reason TEXT NOT NULL,  -- 'duplicate', 'rate_limit', 'maintenance_window', etc.
    dedup_key TEXT,
    metadata JSONB  -- Additional context
);

-- Create indexes for performance
CREATE INDEX idx_dedup_key ON detection_deduplication(tenant_id, rule_id, dedup_key);
CREATE INDEX idx_dedup_status ON detection_deduplication(tenant_id, status, last_seen DESC);
CREATE INDEX idx_suppression_rules_tenant ON detection_suppression_rules(tenant_id, enabled);
CREATE INDEX idx_suppression_events_tenant ON detection_suppression_events(tenant_id, suppressed_at DESC);
CREATE INDEX idx_suppression_events_dedup ON detection_suppression_events(dedup_id);

-- Partial index for active deduplications (most queried)
CREATE INDEX idx_dedup_active ON detection_deduplication(tenant_id, dedup_key, last_seen DESC) 
WHERE status = 'active';

-- Comments
COMMENT ON TABLE detection_deduplication IS 'Tracks duplicate detection patterns to prevent alert fatigue';
COMMENT ON TABLE detection_suppression_rules IS 'Configurable rules for when to suppress alerts';
COMMENT ON TABLE detection_suppression_events IS 'Audit log of suppressed detection events';

COMMENT ON COLUMN detection_deduplication.dedup_key IS 'SHA-256 hash of group_by fields for quick lookup';
COMMENT ON COLUMN detection_deduplication.dedup_fields IS 'JSON of fields used for grouping (user.id, source.ip, etc.)';
COMMENT ON COLUMN detection_suppression_rules.group_by_fields IS 'Fields to group by for deduplication (e.g., ["user.id", "source.ip"])';
COMMENT ON COLUMN detection_suppression_rules.escalate_after_count IS 'Create incident after N duplicates (null = never escalate)';

