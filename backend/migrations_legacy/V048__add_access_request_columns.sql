-- Add missing access_requests columns to align with IAM agent models
-- Safe to run multiple times; uses IF NOT EXISTS and backfills defaults

ALTER TABLE access_requests
    ADD COLUMN IF NOT EXISTS requested_for UUID,
    ADD COLUMN IF NOT EXISTS resource_type VARCHAR(100) NOT NULL DEFAULT 'resource',
    ADD COLUMN IF NOT EXISTS resource_id VARCHAR(255) NOT NULL DEFAULT '*',
    ADD COLUMN IF NOT EXISTS action VARCHAR(50) NOT NULL DEFAULT 'read',
    ADD COLUMN IF NOT EXISTS justification TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS reviewer_id UUID,
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS review_comments TEXT,
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS entitlement_id UUID;

-- Backfill NULLs in case columns existed but lacked defaults/values
UPDATE access_requests
SET
    resource_type = COALESCE(resource_type, 'resource'),
    resource_id   = COALESCE(resource_id, '*'),
    action        = COALESCE(action, 'read'),
    justification = COALESCE(justification, '')
WHERE resource_type IS NULL
   OR resource_id IS NULL
   OR action IS NULL
   OR justification IS NULL;
