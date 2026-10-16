-- Migration: Endpoint Agents for SentinelGrid Endpoint Manager
-- Date: 2025-12-03
-- Purpose: Support Wazuh Manager integration for endpoint security agents

-- Endpoint agents table
CREATE TABLE IF NOT EXISTS endpoint_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    wazuh_agent_id VARCHAR(10) NOT NULL UNIQUE,  -- Wazuh's internal ID (e.g., "001", "002")
    agent_name VARCHAR(255) NOT NULL,
    ip_address INET,
    os_platform VARCHAR(100),                     -- linux, windows, macos
    os_version VARCHAR(100),                      -- Ubuntu 22.04, Windows Server 2022, etc.
    agent_version VARCHAR(50) DEFAULT '4.8.0',   -- Wazuh agent version
    registration_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_keepalive TIMESTAMPTZ,                  -- Last time agent checked in
    status VARCHAR(20) DEFAULT 'pending',         -- pending, active, disconnected, removed
    metadata JSONB DEFAULT '{}',                  -- Custom metadata (tags, labels, etc.)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(tenant_id, wazuh_agent_id),
    CHECK (status IN ('pending', 'active', 'disconnected', 'removed'))
);

-- Indexes for performance
CREATE INDEX idx_endpoint_agents_tenant ON endpoint_agents(tenant_id);
CREATE INDEX idx_endpoint_agents_status ON endpoint_agents(tenant_id, status);
CREATE INDEX idx_endpoint_agents_wazuh_id ON endpoint_agents(wazuh_agent_id);
CREATE INDEX idx_endpoint_agents_keepalive ON endpoint_agents(last_keepalive DESC);
CREATE INDEX idx_endpoint_agents_name ON endpoint_agents(agent_name);

-- Comments for documentation
COMMENT ON TABLE endpoint_agents IS 'SentinelGrid Endpoint Protection agents (Wazuh-based) with multi-tenant isolation';
COMMENT ON COLUMN endpoint_agents.wazuh_agent_id IS 'Wazuh Manager internal agent ID (e.g., 001, 002, 003)';
COMMENT ON COLUMN endpoint_agents.tenant_id IS 'Globally unique tenant ID - used for Wazuh agent labels and event isolation';
COMMENT ON COLUMN endpoint_agents.status IS 'Agent connection status: pending (registered but not connected), active (connected), disconnected (>15min offline), removed (deleted)';
COMMENT ON COLUMN endpoint_agents.agent_version IS 'Wazuh agent version (e.g., 4.8.0)';
COMMENT ON COLUMN endpoint_agents.last_keepalive IS 'Last time agent sent keepalive message to manager';

-- Agent events table (optional - for quick access without querying OpenSearch)
CREATE TABLE IF NOT EXISTS endpoint_agent_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES endpoint_agents(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,              -- alert, vulnerability, fim, rootcheck, sca, syscollector
    severity VARCHAR(20),                         -- info, low, medium, high, critical
    rule_id VARCHAR(50),                          -- Wazuh rule ID (e.g., "5710")
    rule_level INTEGER,                           -- Wazuh rule level (0-15)
    rule_description TEXT,
    raw_event JSONB,                              -- Full event from OpenSearch
    timestamp TIMESTAMPTZ NOT NULL,               -- Event timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- For deduplication
    event_hash VARCHAR(64),  -- Hash of key fields to prevent duplicate storage
    
    -- Constraints
    CHECK (severity IN ('info', 'low', 'medium', 'high', 'critical')),
    CHECK (event_type IN ('alert', 'vulnerability', 'fim', 'rootcheck', 'sca', 'syscollector', 'other'))
);

-- Indexes for performance
CREATE INDEX idx_endpoint_events_tenant_time ON endpoint_agent_events(tenant_id, timestamp DESC);
CREATE INDEX idx_endpoint_events_agent ON endpoint_agent_events(agent_id, timestamp DESC);
CREATE INDEX idx_endpoint_events_type ON endpoint_agent_events(event_type, severity);
CREATE INDEX idx_endpoint_events_severity ON endpoint_agent_events(tenant_id, severity, timestamp DESC);
CREATE INDEX idx_endpoint_events_rule ON endpoint_agent_events(rule_id);
CREATE INDEX idx_endpoint_events_hash ON endpoint_agent_events(event_hash);

-- Comments
COMMENT ON TABLE endpoint_agent_events IS 'Cached endpoint agent events for quick access without querying OpenSearch SIEM';
COMMENT ON COLUMN endpoint_agent_events.tenant_id IS 'Globally unique tenant ID for multi-tenant isolation';
COMMENT ON COLUMN endpoint_agent_events.event_type IS 'Event type: alert (security alert), vulnerability (CVE), fim (file integrity), rootcheck (policy check), sca (compliance), syscollector (inventory)';
COMMENT ON COLUMN endpoint_agent_events.severity IS 'Event severity based on rule level mapping';
COMMENT ON COLUMN endpoint_agent_events.rule_level IS 'Wazuh rule level: 0-15 (higher = more severe)';
COMMENT ON COLUMN endpoint_agent_events.event_hash IS 'Hash for deduplication - prevents storing same event multiple times';

-- Function to update last_keepalive when agent is active
CREATE OR REPLACE FUNCTION update_agent_keepalive()
RETURNS TRIGGER AS $$
BEGIN
    -- Update endpoint_agents last_keepalive when new event arrives
    UPDATE endpoint_agents
    SET 
        last_keepalive = NEW.timestamp,
        status = CASE 
            WHEN status = 'pending' THEN 'active'
            WHEN status = 'disconnected' THEN 'active'
            ELSE status
        END,
        updated_at = NOW()
    WHERE id = NEW.agent_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update agent status
CREATE TRIGGER update_agent_keepalive_trigger
    AFTER INSERT ON endpoint_agent_events
    FOR EACH ROW
    EXECUTE FUNCTION update_agent_keepalive();

COMMENT ON FUNCTION update_agent_keepalive IS 'Automatically updates agent last_keepalive and status when events arrive';
COMMENT ON TRIGGER update_agent_keepalive_trigger ON endpoint_agent_events IS 'Keeps agent status current based on event activity';

