-- Add signup ticketing preferences and SG ticket branding support

-- Persist signup-selected services and ticketing preference on tenants
ALTER TABLE tenants
    ADD COLUMN IF NOT EXISTS services_selected JSONB,
    ADD COLUMN IF NOT EXISTS ticketing_provider TEXT DEFAULT 'internal',
    ADD COLUMN IF NOT EXISTS ticketing_project TEXT;

COMMENT ON COLUMN tenants.services_selected IS 'Selected services/add-ons captured during signup';
COMMENT ON COLUMN tenants.ticketing_provider IS 'Ticketing system preference: internal, jira, servicenow';
COMMENT ON COLUMN tenants.ticketing_project IS 'Project/key/queue identifier for the chosen ticketing system';

-- Store SG public id context and external vendor ids on tickets
ALTER TABLE tickets
    ADD COLUMN IF NOT EXISTS tenant_slug TEXT,
    ADD COLUMN IF NOT EXISTS external_vendor_id TEXT;

COMMENT ON COLUMN tickets.tenant_slug IS 'Tenant slug used for SG-branded ticket identifiers';
COMMENT ON COLUMN tickets.external_vendor_id IS 'Underlying provider ticket id (hidden from end users)';
