-- Playbook Editor Database Schema
-- Migration: V1 - Create playbooks schema

-- Playbooks table
CREATE TABLE IF NOT EXISTS playbooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  category VARCHAR(50),
  version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
  
  -- React Flow workflow structure (JSONB)
  workflow JSONB NOT NULL DEFAULT '{"nodes": [], "edges": []}'::jsonb,
  
  -- Execution config
  timeout_seconds INTEGER DEFAULT 3600,
  retry_policy JSONB,
  on_failure VARCHAR(50) DEFAULT 'fail',
  
  -- Metadata
  is_template BOOLEAN DEFAULT false,
  requires_approval BOOLEAN DEFAULT false,
  tags TEXT[] DEFAULT ARRAY[]::TEXT[],
  trigger_conditions JSONB,
  auto_trigger_enabled BOOLEAN DEFAULT false,
  trigger_priority INTEGER DEFAULT 0,
  
  -- n8n integration (for future)
  n8n_workflow_id VARCHAR(255),
  n8n_webhook_url TEXT,
  
  created_by UUID,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  CONSTRAINT unique_playbook_name_version UNIQUE(tenant_id, name, version)
);

CREATE INDEX IF NOT EXISTS idx_playbooks_tenant_category ON playbooks(tenant_id, category);
CREATE INDEX IF NOT EXISTS idx_playbooks_n8n_workflow_id ON playbooks(n8n_workflow_id);
CREATE INDEX IF NOT EXISTS idx_playbooks_is_template ON playbooks(is_template);

-- Playbook executions table
CREATE TABLE IF NOT EXISTS playbook_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
  tenant_id UUID NOT NULL,
  
  -- Execution context
  trigger_type VARCHAR(50), -- 'alert', 'incident', 'manual', 'scheduled'
  trigger_id UUID,          -- alert_id, incident_id, etc.
  
  -- Status
  status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed', 'cancelled'
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  
  -- n8n integration (for future)
  n8n_execution_id VARCHAR(255),
  
  -- Results
  result JSONB,
  error_message TEXT,
  logs JSONB DEFAULT '[]'::jsonb,
  
  created_at TIMESTAMP DEFAULT NOW(),
  
  CONSTRAINT fk_playbook_executions_playbook FOREIGN KEY (playbook_id) REFERENCES playbooks(id)
);

CREATE INDEX IF NOT EXISTS idx_playbook_executions_playbook ON playbook_executions(playbook_id);
CREATE INDEX IF NOT EXISTS idx_playbook_executions_status ON playbook_executions(status);
CREATE INDEX IF NOT EXISTS idx_playbook_executions_tenant ON playbook_executions(tenant_id);
-- Ensure columns exist if table was created previously without them
ALTER TABLE IF EXISTS playbook_executions
  ADD COLUMN IF NOT EXISTS trigger_type VARCHAR(50),
  ADD COLUMN IF NOT EXISTS trigger_id UUID;
CREATE INDEX IF NOT EXISTS idx_playbook_executions_trigger ON playbook_executions(trigger_type, trigger_id);

-- Observable definitions table
CREATE TABLE IF NOT EXISTS playbook_observables (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
  node_id VARCHAR(255) NOT NULL, -- React Flow node ID
  
  data_type VARCHAR(50) NOT NULL, -- 'ip', 'domain', 'hash', etc.
  extraction_path TEXT, -- JSONPath/XPath
  tags TEXT[] DEFAULT ARRAY[]::TEXT[],
  mark_as_ioc BOOLEAN DEFAULT false,
  
  created_at TIMESTAMP DEFAULT NOW(),
  
  CONSTRAINT unique_playbook_observable_node UNIQUE(playbook_id, node_id),
  CONSTRAINT fk_playbook_observables_playbook FOREIGN KEY (playbook_id) REFERENCES playbooks(id)
);

CREATE INDEX IF NOT EXISTS idx_playbook_observables_playbook ON playbook_observables(playbook_id);

-- Analyzer definitions table
CREATE TABLE IF NOT EXISTS playbook_analyzers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
  node_id VARCHAR(255) NOT NULL, -- React Flow node ID
  
  analyzer_id VARCHAR(255) NOT NULL, -- TheHive analyzer ID
  observable_node_id VARCHAR(255) NOT NULL, -- Node providing observable
  parameters JSONB DEFAULT '{}'::jsonb,
  
  created_at TIMESTAMP DEFAULT NOW(),
  
  CONSTRAINT unique_playbook_analyzer_node UNIQUE(playbook_id, node_id),
  CONSTRAINT fk_playbook_analyzers_playbook FOREIGN KEY (playbook_id) REFERENCES playbooks(id)
);

CREATE INDEX IF NOT EXISTS idx_playbook_analyzers_playbook ON playbook_analyzers(playbook_id);

-- Comments for documentation
COMMENT ON TABLE playbooks IS 'SOAR playbooks stored as React Flow workflows';
COMMENT ON TABLE playbook_executions IS 'Execution history for playbooks';
COMMENT ON TABLE playbook_observables IS 'Observable extraction definitions per playbook node';
COMMENT ON TABLE playbook_analyzers IS 'Analyzer execution definitions per playbook node';
