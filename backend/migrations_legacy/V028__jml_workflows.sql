-- Migration: JML (Joiner/Mover/Leaver) Workflows
-- Date: 2025-12-02
-- Purpose: Automated onboarding, role changes, and offboarding for SOC 2 CC6.3 compliance

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- JML workflows
CREATE TABLE IF NOT EXISTS jml_workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL,
    workflow_type VARCHAR(50) NOT NULL, -- 'joiner', 'mover', 'leaver'
    
    -- Subject information
    subject_user_id TEXT, -- User being processed (NULL for new joiners)
    target_email VARCHAR(255) NOT NULL,
    target_name VARCHAR(255),
    target_profile_id UUID REFERENCES access_profiles(id),
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'failed', 'cancelled'
    initiated_by TEXT NOT NULL,
    initiated_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Steps configuration and status
    steps JSONB, -- Array of workflow steps with status
    
    -- Results
    result_user_id TEXT, -- Created/modified user ID
    error_message TEXT,
    
    -- Metadata
    metadata JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_jml_workflows_tenant_realm ON jml_workflows(tenant_id, realm_name);
CREATE INDEX idx_jml_workflows_type ON jml_workflows(workflow_type);
CREATE INDEX idx_jml_workflows_status ON jml_workflows(status);
CREATE INDEX idx_jml_workflows_subject ON jml_workflows(subject_user_id);
CREATE INDEX idx_jml_workflows_initiated_at ON jml_workflows(initiated_at DESC);

-- JML workflow steps (detailed step tracking)
CREATE TABLE IF NOT EXISTS jml_workflow_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID NOT NULL REFERENCES jml_workflows(id) ON DELETE CASCADE,
    step_name VARCHAR(100) NOT NULL,
    step_type VARCHAR(100) NOT NULL, -- 'create_user', 'assign_entitlements', 'send_email', 'disable_user', etc.
    step_order INTEGER NOT NULL,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'failed', 'skipped'
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    
    -- Results
    result_data JSONB,
    error_message TEXT,
    
    -- Retry information
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_jml_steps_workflow ON jml_workflow_steps(workflow_id);
CREATE INDEX idx_jml_steps_type ON jml_workflow_steps(step_type);
CREATE INDEX idx_jml_steps_status ON jml_workflow_steps(status);
CREATE INDEX idx_jml_steps_order ON jml_workflow_steps(workflow_id, step_order);

-- Comments
COMMENT ON TABLE jml_workflows IS 'Joiner/Mover/Leaver workflows for user lifecycle management';
COMMENT ON COLUMN jml_workflows.workflow_type IS 'Type: joiner (onboarding), mover (role change), leaver (offboarding)';
COMMENT ON COLUMN jml_workflows.steps IS 'JSON array of workflow steps configuration';
COMMENT ON TABLE jml_workflow_steps IS 'Detailed step tracking for JML workflows';

