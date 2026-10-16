-- ============================================================================
-- V003: Row-Level Security (RLS) for multi-tenant isolation
-- ============================================================================
--
-- This migration:
--   1. Creates a helper function to read the current tenant from a session var.
--   2. Adds tenant_id to junction / child tables that are missing it and
--      backfills from their parent tables.
--   3. Enables RLS on every table that carries a tenant_id column.
--   4. Creates per-table policies:
--        - tenant_isolation_select  (FOR SELECT)
--        - tenant_isolation_modify  (FOR INSERT, UPDATE, DELETE)
--        - superadmin_bypass        (unrestricted when session flag is set)
--
-- The migration is idempotent where possible (IF NOT EXISTS / OR REPLACE).
-- Flyway runs each versioned migration inside a single transaction by default.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. Tenant-resolution helper function
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS uuid AS $$
  SELECT NULLIF(current_setting('app.current_tenant_id', true), '')::uuid;
$$ LANGUAGE sql STABLE;

COMMENT ON FUNCTION current_tenant_id() IS
  'Returns the tenant UUID stored in the session variable app.current_tenant_id. '
  'Returns NULL when the variable is unset, which causes RLS policies to deny access.';

-- ---------------------------------------------------------------------------
-- 2. Add tenant_id to security_ops child / junction tables and backfill
-- ---------------------------------------------------------------------------
-- Each block:
--   a) Adds a nullable tenant_id column
--   b) Backfills from the parent table via the FK relationship
--   c) Sets NOT NULL after backfill
--   d) Adds an index for policy evaluation performance
-- ---------------------------------------------------------------------------

-- 2a. security_ops.incident_actions  (parent: incidents)
ALTER TABLE security_ops.incident_actions
  ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE security_ops.incident_actions ia
   SET tenant_id = i.tenant_id
  FROM security_ops.incidents i
 WHERE ia.incident_id = i.id
   AND ia.tenant_id IS NULL;

ALTER TABLE security_ops.incident_actions
  ALTER COLUMN tenant_id SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
      FROM pg_constraint
     WHERE conname = 'incident_actions_tenant_id_fkey'
       AND conrelid = 'security_ops.incident_actions'::regclass
  ) THEN
    ALTER TABLE security_ops.incident_actions
      ADD CONSTRAINT incident_actions_tenant_id_fkey
      FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);
  END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_incident_actions_tenant
  ON security_ops.incident_actions (tenant_id);

-- 2b. security_ops.incident_alerts  (parent: incidents)
ALTER TABLE security_ops.incident_alerts
  ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE security_ops.incident_alerts ia
   SET tenant_id = i.tenant_id
  FROM security_ops.incidents i
 WHERE ia.incident_id = i.id
   AND ia.tenant_id IS NULL;

ALTER TABLE security_ops.incident_alerts
  ALTER COLUMN tenant_id SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
      FROM pg_constraint
     WHERE conname = 'incident_alerts_tenant_id_fkey'
       AND conrelid = 'security_ops.incident_alerts'::regclass
  ) THEN
    ALTER TABLE security_ops.incident_alerts
      ADD CONSTRAINT incident_alerts_tenant_id_fkey
      FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);
  END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_incident_alerts_tenant
  ON security_ops.incident_alerts (tenant_id);

-- 2c. security_ops.incident_evidence  (parent: incidents)
ALTER TABLE security_ops.incident_evidence
  ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE security_ops.incident_evidence ie
   SET tenant_id = i.tenant_id
  FROM security_ops.incidents i
 WHERE ie.incident_id = i.id
   AND ie.tenant_id IS NULL;

ALTER TABLE security_ops.incident_evidence
  ALTER COLUMN tenant_id SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
      FROM pg_constraint
     WHERE conname = 'incident_evidence_tenant_id_fkey'
       AND conrelid = 'security_ops.incident_evidence'::regclass
  ) THEN
    ALTER TABLE security_ops.incident_evidence
      ADD CONSTRAINT incident_evidence_tenant_id_fkey
      FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);
  END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_incident_evidence_tenant
  ON security_ops.incident_evidence (tenant_id);

-- 2d. security_ops.incident_lifecycle  (parent: incidents)
ALTER TABLE security_ops.incident_lifecycle
  ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE security_ops.incident_lifecycle il
   SET tenant_id = i.tenant_id
  FROM security_ops.incidents i
 WHERE il.incident_id = i.id
   AND il.tenant_id IS NULL;

ALTER TABLE security_ops.incident_lifecycle
  ALTER COLUMN tenant_id SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
      FROM pg_constraint
     WHERE conname = 'incident_lifecycle_tenant_id_fkey'
       AND conrelid = 'security_ops.incident_lifecycle'::regclass
  ) THEN
    ALTER TABLE security_ops.incident_lifecycle
      ADD CONSTRAINT incident_lifecycle_tenant_id_fkey
      FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);
  END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_incident_lifecycle_tenant
  ON security_ops.incident_lifecycle (tenant_id);

-- 2e. security_ops.incident_observables  (parent: incidents)
ALTER TABLE security_ops.incident_observables
  ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE security_ops.incident_observables io
   SET tenant_id = i.tenant_id
  FROM security_ops.incidents i
 WHERE io.incident_id = i.id
   AND io.tenant_id IS NULL;

ALTER TABLE security_ops.incident_observables
  ALTER COLUMN tenant_id SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
      FROM pg_constraint
     WHERE conname = 'incident_observables_tenant_id_fkey'
       AND conrelid = 'security_ops.incident_observables'::regclass
  ) THEN
    ALTER TABLE security_ops.incident_observables
      ADD CONSTRAINT incident_observables_tenant_id_fkey
      FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);
  END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_incident_observables_tenant
  ON security_ops.incident_observables (tenant_id);

-- 2f. security_ops.incident_timeline  (parent: incidents)
ALTER TABLE security_ops.incident_timeline
  ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE security_ops.incident_timeline it
   SET tenant_id = i.tenant_id
  FROM security_ops.incidents i
 WHERE it.incident_id = i.id
   AND it.tenant_id IS NULL;

ALTER TABLE security_ops.incident_timeline
  ALTER COLUMN tenant_id SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
      FROM pg_constraint
     WHERE conname = 'incident_timeline_tenant_id_fkey'
       AND conrelid = 'security_ops.incident_timeline'::regclass
  ) THEN
    ALTER TABLE security_ops.incident_timeline
      ADD CONSTRAINT incident_timeline_tenant_id_fkey
      FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);
  END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_incident_timeline_tenant
  ON security_ops.incident_timeline (tenant_id);

-- 2g. security_ops.ticket_alerts  (parent: tickets)
ALTER TABLE security_ops.ticket_alerts
  ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE security_ops.ticket_alerts ta
   SET tenant_id = t.tenant_id
  FROM security_ops.tickets t
 WHERE ta.ticket_id = t.id
   AND ta.tenant_id IS NULL;

ALTER TABLE security_ops.ticket_alerts
  ALTER COLUMN tenant_id SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
      FROM pg_constraint
     WHERE conname = 'ticket_alerts_tenant_id_fkey'
       AND conrelid = 'security_ops.ticket_alerts'::regclass
  ) THEN
    ALTER TABLE security_ops.ticket_alerts
      ADD CONSTRAINT ticket_alerts_tenant_id_fkey
      FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);
  END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_ticket_alerts_tenant
  ON security_ops.ticket_alerts (tenant_id);

-- 2h. security_ops.ticket_vulnerabilities  (parent: tickets)
ALTER TABLE security_ops.ticket_vulnerabilities
  ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE security_ops.ticket_vulnerabilities tv
   SET tenant_id = t.tenant_id
  FROM security_ops.tickets t
 WHERE tv.ticket_id = t.id
   AND tv.tenant_id IS NULL;

ALTER TABLE security_ops.ticket_vulnerabilities
  ALTER COLUMN tenant_id SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
      FROM pg_constraint
     WHERE conname = 'ticket_vulnerabilities_tenant_id_fkey'
       AND conrelid = 'security_ops.ticket_vulnerabilities'::regclass
  ) THEN
    ALTER TABLE security_ops.ticket_vulnerabilities
      ADD CONSTRAINT ticket_vulnerabilities_tenant_id_fkey
      FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);
  END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_ticket_vulnerabilities_tenant
  ON security_ops.ticket_vulnerabilities (tenant_id);

-- 2i. security_ops.detection_rule_versions  (parent: detection_rules)
ALTER TABLE security_ops.detection_rule_versions
  ADD COLUMN IF NOT EXISTS tenant_id uuid;

UPDATE security_ops.detection_rule_versions drv
   SET tenant_id = dr.tenant_id
  FROM security_ops.detection_rules dr
 WHERE drv.rule_id = dr.id
   AND drv.tenant_id IS NULL;

ALTER TABLE security_ops.detection_rule_versions
  ALTER COLUMN tenant_id SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
      FROM pg_constraint
     WHERE conname = 'detection_rule_versions_tenant_id_fkey'
       AND conrelid = 'security_ops.detection_rule_versions'::regclass
  ) THEN
    ALTER TABLE security_ops.detection_rule_versions
      ADD CONSTRAINT detection_rule_versions_tenant_id_fkey
      FOREIGN KEY (tenant_id) REFERENCES public.tenants(id);
  END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_detection_rule_versions_tenant
  ON security_ops.detection_rule_versions (tenant_id);


-- ============================================================================
-- 3. Enable RLS and create policies on ALL tenant-scoped tables
-- ============================================================================
--
-- We use a DO block to iterate over every (schema, table) pair so the policy
-- creation is compact, consistent, and hard to get out of sync.
-- ============================================================================

DO $rls$
DECLARE
  _tbl RECORD;
  _tenant_predicate text;
BEGIN
  -- -------------------------------------------------------------------
  -- Enumerate every table that must have RLS.
  -- The list is kept explicit (not introspected) so that the migration
  -- is deterministic and auditable.
  -- -------------------------------------------------------------------
  FOR _tbl IN
    SELECT schema_name, table_name
      FROM (VALUES
        -- == public schema ==
        ('public', 'access_profiles'),
        ('public', 'access_requests'),
        ('public', 'access_review_campaigns'),
        ('public', 'access_review_decisions'),
        ('public', 'access_review_items'),
        ('public', 'access_review_statistics'),
        ('public', 'adapter_training_jobs'),
        ('public', 'adapter_version_history'),
        ('public', 'agent_bootstrap_tokens'),
        ('public', 'api_keys'),
        ('public', 'apps'),
        ('public', 'assets'),
        ('public', 'birthright_rules'),
        ('public', 'ca_authorities'),
        ('public', 'certificate_requests'),
        ('public', 'certificates'),
        ('public', 'chat_messages'),
        ('public', 'chat_sessions'),
        ('public', 'connected_apps'),
        ('public', 'cybersecurity_knowledge_base'),
        ('public', 'devices'),
        ('public', 'endpoint_agent_events'),
        ('public', 'endpoint_agents'),
        ('public', 'entitlement_mappings'),
        ('public', 'entitlements'),
        ('public', 'evidence_collection_tasks'),
        ('public', 'evidence_items'),
        ('public', 'evidence_packages'),
        ('public', 'findings'),
        ('public', 'fix_group_assets'),
        ('public', 'fix_group_cves'),
        ('public', 'fix_groups'),
        ('public', 'iam_audit_log'),
        ('public', 'iam_findings'),
        ('public', 'integrations'),
        ('public', 'jml_workflows'),
        ('public', 'jobs'),
        ('public', 'mfa_compliance_violations'),
        ('public', 'mfa_enforcement_policies'),
        ('public', 'model_inference_logs'),
        ('public', 'phishing_observables'),
        ('public', 'phishing_reports'),
        ('public', 'playbook_executions'),
        ('public', 'policy_conflicts'),
        ('public', 'policy_evaluations'),
        ('public', 'policy_templates'),
        ('public', 'posture_findings'),
        ('public', 'privileged_access_requests'),
        ('public', 'remediation_metadata'),
        ('public', 'scans'),
        ('public', 'secrets'),
        ('public', 'security_event_embeddings'),
        ('public', 'tenant_control_status'),
        ('public', 'tenant_detection_monitors'),
        ('public', 'tenant_model_adapters'),
        ('public', 'tenant_provisioning_log'),
        ('public', 'tenant_training_data'),
        ('public', 'training_data_snapshots'),
        ('public', 'user_entitlements'),
        ('public', 'user_lifecycle_schedule'),
        ('public', 'user_mfa_status'),
        ('public', 'user_tenants'),
        ('public', 'vault_access_grants'),
        ('public', 'vault_audit_log'),
        ('public', 'vault_tenants'),
        ('public', 'vault_usage_history'),
        ('public', 'vulnerabilities'),

        -- == audit schema ==
        ('audit', 'audit_log_statistics'),
        ('audit', 'audit_retention_policies'),
        ('audit', 'platform_audit_logs'),

        -- == orchestration schema ==
        ('orchestration', 'scans'),

        -- == reporting schema ==
        ('reporting', 'generated_reports'),
        ('reporting', 'report_access_log'),
        ('reporting', 'report_llm_documents'),
        ('reporting', 'report_schedules'),
        ('reporting', 'report_shares'),
        ('reporting', 'report_templates'),
        ('reporting', 'reports'),

        -- == security_ops schema (tables that already had tenant_id) ==
        ('security_ops', 'alert_ai_analysis'),
        ('security_ops', 'alert_playbook_triggers'),
        ('security_ops', 'alert_triage_feedback'),
        ('security_ops', 'alerts'),
        ('security_ops', 'detection_bindings'),
        ('security_ops', 'detection_deduplication'),
        ('security_ops', 'detection_playbook_mappings'),
        ('security_ops', 'detection_rule_executions'),
        ('security_ops', 'detection_rules'),
        ('security_ops', 'detection_suppression_events'),
        ('security_ops', 'detection_suppression_rules'),
        ('security_ops', 'incidents'),
        ('security_ops', 'playbooks'),
        ('security_ops', 'ticket_ai_enrichments'),
        ('security_ops', 'tickets'),

        -- == security_ops schema (tables that gained tenant_id above) ==
        ('security_ops', 'detection_rule_versions'),
        ('security_ops', 'incident_actions'),
        ('security_ops', 'incident_alerts'),
        ('security_ops', 'incident_evidence'),
        ('security_ops', 'incident_lifecycle'),
        ('security_ops', 'incident_observables'),
        ('security_ops', 'incident_timeline'),
        ('security_ops', 'ticket_alerts'),
        ('security_ops', 'ticket_vulnerabilities')
      ) AS t(schema_name, table_name)
  LOOP
    IF (_tbl.schema_name, _tbl.table_name) IN (
      ('reporting', 'report_shares'),
      ('reporting', 'report_templates'),
      ('reporting', 'reports')
    ) THEN
      _tenant_predicate := 'tenant_id = current_tenant_id()::text';
    ELSE
      _tenant_predicate := 'tenant_id = current_tenant_id()';
    END IF;

    -- Enable RLS on the table
    EXECUTE format(
      'ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY',
      _tbl.schema_name, _tbl.table_name
    );

    -- Force RLS even for table owners (defense in depth)
    EXECUTE format(
      'ALTER TABLE %I.%I FORCE ROW LEVEL SECURITY',
      _tbl.schema_name, _tbl.table_name
    );

    -- Policy: tenant_isolation_select  (FOR SELECT)
    EXECUTE format(
      'CREATE POLICY tenant_isolation_select ON %I.%I '
      'FOR SELECT USING (%s)',
      _tbl.schema_name, _tbl.table_name, _tenant_predicate
    );

    -- Policy: tenant_isolation_modify  (FOR ALL — covers INSERT, UPDATE, DELETE)
    -- Uses WITH CHECK for INSERT/UPDATE validation and USING for UPDATE/DELETE visibility.
    EXECUTE format(
      'CREATE POLICY tenant_isolation_modify ON %I.%I '
      'FOR ALL USING (%s) '
      'WITH CHECK (%s)',
      _tbl.schema_name, _tbl.table_name, _tenant_predicate, _tenant_predicate
    );

    -- Policy: superadmin_bypass  (unrestricted access when session flag is set)
    EXECUTE format(
      'CREATE POLICY superadmin_bypass ON %I.%I '
      'USING (current_setting(''app.is_superadmin'', true) = ''true'')',
      _tbl.schema_name, _tbl.table_name
    );

  END LOOP;
END
$rls$;

-- ============================================================================
-- Done.  Summary:
--   - 1 helper function   : current_tenant_id()
--   - 9 tables gained      tenant_id (backfilled, NOT NULL, indexed, FK'd)
--   - 97 tables now have   RLS enabled + FORCE
--   - 3 policies per table : tenant_isolation_select,
--                            tenant_isolation_modify,
--                            superadmin_bypass
-- ============================================================================
