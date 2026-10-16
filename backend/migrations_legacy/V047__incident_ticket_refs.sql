-- Add ticket references to incidents
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS ticket_id UUID NULL REFERENCES tickets(id) ON DELETE SET NULL;
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS external_ticket_id TEXT NULL;
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS external_ticket_provider TEXT NULL;

COMMENT ON COLUMN incidents.ticket_id IS 'Internal ticket record linked to incident';
COMMENT ON COLUMN incidents.external_ticket_id IS 'External ticket id (e.g., Zammad case id)';
COMMENT ON COLUMN incidents.external_ticket_provider IS 'External provider name (zammad/thehive/etc.)';
