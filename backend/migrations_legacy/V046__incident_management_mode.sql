-- Add incident_management_mode to tenants
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS incident_management_mode TEXT NOT NULL DEFAULT 'saas_managed';

COMMENT ON COLUMN tenants.incident_management_mode IS 'Incident handling mode: saas_managed or customer_managed';
