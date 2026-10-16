-- Add ticket linkage columns to fix_groups
ALTER TABLE fix_groups
    ADD COLUMN IF NOT EXISTS ticket_id TEXT,
    ADD COLUMN IF NOT EXISTS ticket_status VARCHAR(32);
