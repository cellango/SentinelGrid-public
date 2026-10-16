-- Ensure ca_authorities supports tenant isolation (cert service)
-- Safe/idempotent: adds columns/index/comments if missing and leaves existing data intact.

ALTER TABLE ca_authorities
  ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS ca_name VARCHAR(255),
  ADD COLUMN IF NOT EXISTS certificate_profile VARCHAR(100),
  ADD COLUMN IF NOT EXISTS enrollment_protocols JSONB;

CREATE INDEX IF NOT EXISTS idx_ca_authorities_tenant_id ON ca_authorities(tenant_id);

UPDATE ca_authorities SET tenant_id = NULL WHERE tenant_id IS NULL;

COMMENT ON COLUMN ca_authorities.tenant_id IS 'Tenant ID for per-tenant CA isolation. NULL = shared CA for all tenants.';
COMMENT ON COLUMN ca_authorities.ca_name IS 'CA name in EJBCA (e.g., SentinelGrid-Issuing-CA)';
COMMENT ON COLUMN ca_authorities.certificate_profile IS 'Certificate profile name in EJBCA (e.g., service-tls)';
COMMENT ON COLUMN ca_authorities.enrollment_protocols IS 'Array of supported enrollment protocols: acme, scep, est';
