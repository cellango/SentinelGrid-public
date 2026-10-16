-- Hero Flow 4 & 5 - Schema Enhancements
-- Migration: 006 - Enhance existing tables for automated response and compliance remediation
-- Date: 2025-01-28
-- 
-- Key Principle: Enhance existing open-source tool schemas, don't duplicate them.
-- This migration adds trigger conditions to playbooks and remediation fields to findings.

-- ============================================================================
-- PART 1: Enhance Playbooks Table (Hero Flow 4 - Automated Response)
-- ============================================================================

-- Add trigger conditions for automated playbook triggering
ALTER TABLE playbooks 
ADD COLUMN IF NOT EXISTS trigger_conditions JSONB;

-- Enable/disable automatic triggering
ALTER TABLE playbooks 
ADD COLUMN IF NOT EXISTS auto_trigger_enabled BOOLEAN DEFAULT false;

-- Priority for trigger evaluation (higher priority = evaluated first)
ALTER TABLE playbooks 
ADD COLUMN IF NOT EXISTS trigger_priority INTEGER DEFAULT 0;

-- Add comments
COMMENT ON COLUMN playbooks.trigger_conditions IS 'Alert criteria for automatic playbook triggering (e.g., severity, category, source)';
COMMENT ON COLUMN playbooks.auto_trigger_enabled IS 'Whether this playbook should be automatically triggered when conditions match';
COMMENT ON COLUMN playbooks.trigger_priority IS 'Priority for trigger evaluation (higher = evaluated first)';

-- ============================================================================
-- PART 2: Enhance Playbook Executions Table (Hero Flow 4 - Alert Linkage)
-- ============================================================================

-- Link playbook execution to alert (if triggered by alert)
ALTER TABLE playbook_executions 
ADD COLUMN IF NOT EXISTS alert_id UUID REFERENCES alerts(id);

-- Track how the playbook was triggered
-- Note: 'triggered_by' may already exist - this is safe with IF NOT EXISTS
ALTER TABLE playbook_executions 
ADD COLUMN IF NOT EXISTS triggered_by VARCHAR(50) DEFAULT 'manual'; -- 'manual', 'rule', 'alert', 'scheduled'

-- Reference to the playbook that triggered this (for cascading playbooks)
ALTER TABLE playbook_executions 
ADD COLUMN IF NOT EXISTS trigger_rule_id UUID REFERENCES playbooks(id);

-- Add comments
COMMENT ON COLUMN playbook_executions.alert_id IS 'Alert that triggered this playbook execution (if applicable)';
COMMENT ON COLUMN playbook_executions.triggered_by IS 'How this playbook was triggered: manual, rule, alert, scheduled';
COMMENT ON COLUMN playbook_executions.trigger_rule_id IS 'Playbook that triggered this execution (for cascading playbooks)';

-- ============================================================================
-- PART 3: Create IAM Findings Table (if it doesn't exist) and Enhance
-- ============================================================================

-- Create iam_findings table if it doesn't exist
CREATE TABLE IF NOT EXISTS iam_findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    identity_id UUID, -- References iam_identities(id) if that table exists
    finding_type VARCHAR(100) NOT NULL, -- 'dormant_account', 'overprivileged', 'missing_mfa', etc.
    severity VARCHAR(50) NOT NULL, -- 'critical', 'high', 'medium', 'low'
    description TEXT NOT NULL,
    recommendation TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'open', -- 'open', 'accepted', 'resolved', 'false_positive'
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Add compliance remediation fields (Hero Flow 5)
ALTER TABLE iam_findings 
ADD COLUMN IF NOT EXISTS nist_control_id VARCHAR(100);

ALTER TABLE iam_findings 
ADD COLUMN IF NOT EXISTS remediation_plan JSONB;

ALTER TABLE iam_findings 
ADD COLUMN IF NOT EXISTS remediation_status VARCHAR(50) DEFAULT 'open'; -- 'open', 'in_progress', 'resolved', 'failed'

ALTER TABLE iam_findings 
ADD COLUMN IF NOT EXISTS remediated_at TIMESTAMPTZ;

ALTER TABLE iam_findings 
ADD COLUMN IF NOT EXISTS remediated_by UUID; -- User ID who remediated

-- Add comments
COMMENT ON COLUMN iam_findings.nist_control_id IS 'NIST SP 800-53 control ID associated with this finding';
COMMENT ON COLUMN iam_findings.remediation_plan IS 'Structured remediation plan (steps, actions, playbook references)';
COMMENT ON COLUMN iam_findings.remediation_status IS 'Status of remediation: open, in_progress, resolved, failed';
COMMENT ON COLUMN iam_findings.remediated_at IS 'Timestamp when remediation was completed';
COMMENT ON COLUMN iam_findings.remediated_by IS 'User ID who executed the remediation';

-- ============================================================================
-- PART 4: Create Posture Findings Table (if it doesn't exist) and Enhance
-- ============================================================================

-- Create posture_findings table if it doesn't exist
CREATE TABLE IF NOT EXISTS posture_findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cloud_account_id UUID, -- References cloud_accounts(id) if that table exists
    scan_id UUID, -- References posture_scans(id) if that table exists
    check_id VARCHAR(255), -- Prowler check ID or similar
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    severity VARCHAR(50) NOT NULL, -- 'critical', 'high', 'medium', 'low'
    resource_id VARCHAR(500), -- Affected cloud resource
    service VARCHAR(100), -- 's3', 'iam', 'ec2', 'rds', etc.
    category VARCHAR(100), -- 'network', 'identity', 'logging', 'encryption', etc.
    framework VARCHAR(100), -- 'CIS', 'NIST', 'PCI', etc.
    remediation TEXT, -- Remediation steps from tool
    status VARCHAR(50) NOT NULL DEFAULT 'open', -- 'open', 'accepted', 'fixed', 'false_positive'
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Add compliance remediation fields (Hero Flow 5)
ALTER TABLE posture_findings 
ADD COLUMN IF NOT EXISTS nist_control_id VARCHAR(100);

ALTER TABLE posture_findings 
ADD COLUMN IF NOT EXISTS remediation_plan JSONB;

ALTER TABLE posture_findings 
ADD COLUMN IF NOT EXISTS remediation_status VARCHAR(50) DEFAULT 'open';

ALTER TABLE posture_findings 
ADD COLUMN IF NOT EXISTS remediated_at TIMESTAMPTZ;

ALTER TABLE posture_findings 
ADD COLUMN IF NOT EXISTS remediated_by UUID;

-- Add comments
COMMENT ON COLUMN posture_findings.nist_control_id IS 'NIST SP 800-53 control ID associated with this finding';
COMMENT ON COLUMN posture_findings.remediation_plan IS 'Structured remediation plan (steps, actions, playbook references)';
COMMENT ON COLUMN posture_findings.remediation_status IS 'Status of remediation: open, in_progress, resolved, failed';
COMMENT ON COLUMN posture_findings.remediated_at IS 'Timestamp when remediation was completed';
COMMENT ON COLUMN posture_findings.remediated_by IS 'User ID who executed the remediation';

-- ============================================================================
-- PART 5: Create Metadata Tables (Hero Flow 4 & 5)
-- ============================================================================

-- Metadata table for remediation action tracking (links to playbook_executions)
-- This doesn't duplicate action execution, just tracks remediation-specific metadata
CREATE TABLE IF NOT EXISTS remediation_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    finding_id UUID NOT NULL, -- References iam_findings.id or posture_findings.id
    finding_type VARCHAR(50) NOT NULL, -- 'iam_finding', 'posture_finding'
    playbook_execution_id UUID REFERENCES playbook_executions(id), -- Links to actual execution
    remediation_plan JSONB, -- Structured remediation steps
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'failed'
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE remediation_metadata IS 'Metadata for remediation actions - links findings to playbook executions (metadata only, no duplication)';

-- Metadata table for automated response rule evaluation
-- This tracks which playbooks were triggered by which alerts (metadata only)
CREATE TABLE IF NOT EXISTS alert_playbook_triggers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    alert_id UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    playbook_id UUID NOT NULL REFERENCES playbooks(id),
    playbook_execution_id UUID REFERENCES playbook_executions(id),
    trigger_reason TEXT, -- Why this playbook was triggered
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE alert_playbook_triggers IS 'Metadata tracking which playbooks were triggered by which alerts (metadata only, no duplication)';

-- ============================================================================
-- PART 6: Create Indexes for Performance
-- ============================================================================

-- Indexes for playbook trigger evaluation
CREATE INDEX IF NOT EXISTS idx_playbooks_auto_trigger 
ON playbooks(tenant_id, auto_trigger_enabled) 
WHERE auto_trigger_enabled = true;

CREATE INDEX IF NOT EXISTS idx_playbooks_trigger_priority 
ON playbooks(tenant_id, trigger_priority DESC) 
WHERE auto_trigger_enabled = true;

-- Indexes for playbook execution alert linkage
CREATE INDEX IF NOT EXISTS idx_playbook_executions_alert 
ON playbook_executions(alert_id) 
WHERE alert_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_playbook_executions_triggered_by 
ON playbook_executions(tenant_id, triggered_by);

-- Indexes for IAM findings remediation
CREATE INDEX IF NOT EXISTS idx_iam_findings_remediation 
ON iam_findings(tenant_id, remediation_status);

CREATE INDEX IF NOT EXISTS idx_iam_findings_nist_control 
ON iam_findings(tenant_id, nist_control_id) 
WHERE nist_control_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_iam_findings_status 
ON iam_findings(tenant_id, status);

-- Indexes for posture findings remediation
CREATE INDEX IF NOT EXISTS idx_posture_findings_remediation 
ON posture_findings(tenant_id, remediation_status);

CREATE INDEX IF NOT EXISTS idx_posture_findings_nist_control 
ON posture_findings(tenant_id, nist_control_id) 
WHERE nist_control_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_posture_findings_status 
ON posture_findings(tenant_id, status);

-- Indexes for metadata tables
CREATE INDEX IF NOT EXISTS idx_remediation_metadata_finding 
ON remediation_metadata(finding_id, finding_type);

CREATE INDEX IF NOT EXISTS idx_remediation_metadata_status 
ON remediation_metadata(tenant_id, status);

CREATE INDEX IF NOT EXISTS idx_remediation_metadata_execution 
ON remediation_metadata(playbook_execution_id) 
WHERE playbook_execution_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_alert_playbook_triggers_alert 
ON alert_playbook_triggers(alert_id);

CREATE INDEX IF NOT EXISTS idx_alert_playbook_triggers_playbook 
ON alert_playbook_triggers(playbook_id);

CREATE INDEX IF NOT EXISTS idx_alert_playbook_triggers_execution 
ON alert_playbook_triggers(playbook_execution_id) 
WHERE playbook_execution_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_alert_playbook_triggers_tenant 
ON alert_playbook_triggers(tenant_id);

-- ============================================================================
-- Migration Complete
-- ============================================================================

