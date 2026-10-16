-- ============================================================================
-- V004: Allow shared report template reads under tenant-scoped sessions
-- ============================================================================
--
-- Reporting templates intentionally support seeded system rows where tenant_id
-- is NULL. Those rows are shared product content and should remain readable to
-- authenticated tenant-scoped sessions. Mutations still remain tenant-owned.
-- ============================================================================

DROP POLICY IF EXISTS tenant_isolation_select ON reporting.report_templates;

CREATE POLICY tenant_isolation_select ON reporting.report_templates
  FOR SELECT
  USING (
    tenant_id = current_tenant_id()::text
    OR tenant_id IS NULL
  );
