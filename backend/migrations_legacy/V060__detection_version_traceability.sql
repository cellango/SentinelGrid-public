-- V060: Add traceability and binding tables for detections/playbooks
-- Safe to apply out of order (no destructive changes).

-- 1) Link detection rule versions to query templates (if template/version fields are missing).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='detection_rule_versions' AND column_name='query_template_id'
    ) THEN
        ALTER TABLE detection_rule_versions
        ADD COLUMN query_template_id text,
        ADD COLUMN query_template_version text;
    END IF;
END $$;

-- 2) Link incidents/events to detection_rule_version and playbook_version for traceability.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='incidents') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='incidents' AND column_name='detection_rule_version_id'
        ) THEN
            ALTER TABLE incidents
            ADD COLUMN detection_rule_version_id uuid;
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='incidents' AND column_name='playbook_version_id'
        ) THEN
            ALTER TABLE incidents
            ADD COLUMN playbook_version_id uuid;
        END IF;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='detection_events') THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='detection_events' AND column_name='detection_rule_version_id'
        ) THEN
            ALTER TABLE detection_events
            ADD COLUMN detection_rule_version_id uuid;
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='detection_events' AND column_name='playbook_version_id'
        ) THEN
            ALTER TABLE detection_events
            ADD COLUMN playbook_version_id uuid;
        END IF;
    END IF;
END $$;

-- 3) Detection ↔ playbook mapping (versioned)
CREATE TABLE IF NOT EXISTS detection_playbook_mappings (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    detection_rule_version_id uuid NOT NULL REFERENCES detection_rule_versions(id) ON DELETE CASCADE,
    playbook_version_id uuid NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- 4) Tenant detection bindings (bindings to a specific detection version with overrides)
CREATE TABLE IF NOT EXISTS detection_bindings (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id uuid NOT NULL,
    detection_rule_id uuid NOT NULL REFERENCES detection_rules(id) ON DELETE CASCADE,
    detection_rule_version_id uuid REFERENCES detection_rule_versions(id) ON DELETE SET NULL,
    params_override jsonb DEFAULT '{}'::jsonb,
    is_enabled boolean NOT NULL DEFAULT true,
    rollout_status text DEFAULT 'published',
    destination_id text,
    scope text DEFAULT 'sg', -- sg or tenant
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, detection_rule_id)
);

-- Indexes to speed lookups
CREATE INDEX IF NOT EXISTS idx_detection_bindings_tenant ON detection_bindings (tenant_id);
CREATE INDEX IF NOT EXISTS idx_detection_bindings_scope ON detection_bindings (scope);
