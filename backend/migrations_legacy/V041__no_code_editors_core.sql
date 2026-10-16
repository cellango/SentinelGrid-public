-- Migration: 041 - No-Code Editors Core
-- Adds template/graph/approval fields needed for alarm, playbook, and policy editors

-- Detection rule versions: store visual graph + template flag
ALTER TABLE detection_rule_versions
ADD COLUMN IF NOT EXISTS graph_json JSONB;

ALTER TABLE detection_rule_versions
ADD COLUMN IF NOT EXISTS is_template BOOLEAN DEFAULT false;

-- Detection rules: approval gate before deploy
ALTER TABLE detection_rules
ADD COLUMN IF NOT EXISTS approval_required BOOLEAN DEFAULT false;

-- Tenant monitor deployment status + approval state
ALTER TABLE tenant_detection_monitors
ADD COLUMN IF NOT EXISTS approval_status TEXT DEFAULT 'approved';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_tenant_detection_monitors_approval_status'
    ) THEN
        ALTER TABLE tenant_detection_monitors
        ADD CONSTRAINT ck_tenant_detection_monitors_approval_status
        CHECK (approval_status IN ('pending','approved','rejected'));
    END IF;
END $$;

-- Playbooks: template metadata
ALTER TABLE playbooks
ADD COLUMN IF NOT EXISTS is_template BOOLEAN DEFAULT false;

ALTER TABLE playbooks
ADD COLUMN IF NOT EXISTS template_key TEXT;

-- Playbook executions: enforce valid approval_status values (column exists from initial schema)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_playbook_executions_approval_status'
    ) THEN
        ALTER TABLE playbook_executions
        ADD CONSTRAINT ck_playbook_executions_approval_status
        CHECK (approval_status IN ('pending','approved','rejected'));
    END IF;
END $$;

-- IAM policies: templates + approvals
ALTER TABLE policy_templates
ADD COLUMN IF NOT EXISTS tenant_id UUID NULL REFERENCES tenants(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_policy_templates_tenant_type ON policy_templates(tenant_id, policy_type);

ALTER TABLE policies
ADD COLUMN IF NOT EXISTS is_template BOOLEAN DEFAULT false;

ALTER TABLE policies
ADD COLUMN IF NOT EXISTS approval_required BOOLEAN DEFAULT false;

ALTER TABLE policies
ADD COLUMN IF NOT EXISTS approval_status TEXT DEFAULT 'approved';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_policies_approval_status'
    ) THEN
        ALTER TABLE policies
        ADD CONSTRAINT ck_policies_approval_status
        CHECK (approval_status IN ('pending','approved','rejected'));
    END IF;
END $$;

-- Policy evaluations: store decision trace for tests/debug
ALTER TABLE policy_evaluations
ADD COLUMN IF NOT EXISTS decision_trace JSONB;

-- Backfill any NULL approval statuses to approved
UPDATE tenant_detection_monitors SET approval_status = 'approved' WHERE approval_status IS NULL;
UPDATE policies SET approval_status = 'approved' WHERE approval_status IS NULL;
