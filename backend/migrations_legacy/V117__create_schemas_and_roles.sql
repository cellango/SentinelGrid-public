-- Establish logical schemas and service roles without moving data yet.
-- Schemas: core, security_ops, orchestration, reporting, audit.
-- Roles follow the svc_<service>[_rw|_ro] convention and are NOLOGIN group roles;
-- application login roles can inherit from these.

-- Create schemas (idempotent)
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS security_ops;
CREATE SCHEMA IF NOT EXISTS orchestration;
CREATE SCHEMA IF NOT EXISTS reporting;
CREATE SCHEMA IF NOT EXISTS audit;

-- Helper to create roles if missing
DO $$
DECLARE
  r text;
BEGIN
  FOR r IN
    SELECT unnest(ARRAY[
      'svc_api_gateway_rw',
      'svc_tenant_rw',
      'svc_siem_agent_rw',
      'svc_siem_agent_ro',
      'svc_orch_rw',
      'svc_orch_ro',
      'svc_reporting_ro',
      'svc_incident_rw',
      'svc_framework_rw',
      'svc_model_gateway_rw',
      'svc_audit_rw',
      'svc_audit_ro',
      'svc_readonly'
    ])
  LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('CREATE ROLE %I NOLOGIN', r);
    END IF;
  END LOOP;
END$$;

-- Grant schema usage
GRANT USAGE ON SCHEMA core TO
  svc_api_gateway_rw,
  svc_tenant_rw,
  svc_siem_agent_ro,
  svc_orch_ro,
  svc_framework_rw,
  svc_reporting_ro,
  svc_readonly;

GRANT USAGE ON SCHEMA security_ops TO
  svc_api_gateway_rw,
  svc_siem_agent_rw,
  svc_incident_rw,
  svc_framework_rw,
  svc_reporting_ro,
  svc_readonly;

GRANT USAGE ON SCHEMA orchestration TO
  svc_orch_rw,
  svc_orch_ro,
  svc_reporting_ro,
  svc_readonly;

GRANT USAGE ON SCHEMA reporting TO
  svc_reporting_ro,
  svc_readonly;

GRANT USAGE ON SCHEMA audit TO
  svc_audit_rw,
  svc_audit_ro,
  svc_reporting_ro,
  svc_readonly;

-- Default privileges for objects created by the migration user (sg) in each schema
-- Tables
ALTER DEFAULT PRIVILEGES FOR ROLE sg IN SCHEMA core
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO svc_api_gateway_rw, svc_tenant_rw, svc_framework_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE sg IN SCHEMA core
  GRANT SELECT ON TABLES TO svc_siem_agent_ro, svc_orch_ro, svc_reporting_ro, svc_readonly;

ALTER DEFAULT PRIVILEGES FOR ROLE sg IN SCHEMA security_ops
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO svc_api_gateway_rw, svc_siem_agent_rw, svc_incident_rw, svc_framework_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE sg IN SCHEMA security_ops
  GRANT SELECT ON TABLES TO svc_reporting_ro, svc_readonly;

ALTER DEFAULT PRIVILEGES FOR ROLE sg IN SCHEMA orchestration
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO svc_orch_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE sg IN SCHEMA orchestration
  GRANT SELECT ON TABLES TO svc_orch_ro, svc_reporting_ro, svc_readonly;

ALTER DEFAULT PRIVILEGES FOR ROLE sg IN SCHEMA reporting
  GRANT SELECT ON TABLES TO svc_reporting_ro, svc_readonly;

ALTER DEFAULT PRIVILEGES FOR ROLE sg IN SCHEMA audit
  GRANT INSERT ON TABLES TO svc_audit_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE sg IN SCHEMA audit
  GRANT SELECT ON TABLES TO svc_audit_ro, svc_reporting_ro, svc_readonly;

-- Sequences
ALTER DEFAULT PRIVILEGES FOR ROLE sg IN SCHEMA core
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO svc_api_gateway_rw, svc_tenant_rw, svc_framework_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE sg IN SCHEMA core
  GRANT SELECT ON SEQUENCES TO svc_siem_agent_ro, svc_orch_ro, svc_reporting_ro, svc_readonly;

ALTER DEFAULT PRIVILEGES FOR ROLE sg IN SCHEMA security_ops
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO svc_api_gateway_rw, svc_siem_agent_rw, svc_incident_rw, svc_framework_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE sg IN SCHEMA security_ops
  GRANT SELECT ON SEQUENCES TO svc_reporting_ro, svc_readonly;

ALTER DEFAULT PRIVILEGES FOR ROLE sg IN SCHEMA orchestration
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO svc_orch_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE sg IN SCHEMA orchestration
  GRANT SELECT ON SEQUENCES TO svc_orch_ro, svc_reporting_ro, svc_readonly;

ALTER DEFAULT PRIVILEGES FOR ROLE sg IN SCHEMA reporting
  GRANT SELECT ON SEQUENCES TO svc_reporting_ro, svc_readonly;

ALTER DEFAULT PRIVILEGES FOR ROLE sg IN SCHEMA audit
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO svc_audit_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE sg IN SCHEMA audit
  GRANT SELECT ON SEQUENCES TO svc_audit_ro, svc_reporting_ro, svc_readonly;
