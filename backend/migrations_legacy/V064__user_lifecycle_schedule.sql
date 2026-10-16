-- Scheduled lifecycle dates for user activation/offboarding

CREATE TABLE IF NOT EXISTS user_lifecycle_schedule (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id uuid NOT NULL,
    user_id text NOT NULL,
    activate_at timestamptz,
    deactivate_at timestamptz,
    last_applied_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_lifecycle_unique ON user_lifecycle_schedule (tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_user_lifecycle_activate ON user_lifecycle_schedule (tenant_id, activate_at);
CREATE INDEX IF NOT EXISTS idx_user_lifecycle_deactivate ON user_lifecycle_schedule (tenant_id, deactivate_at);
