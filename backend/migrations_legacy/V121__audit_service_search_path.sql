-- Set search_path for audit_service role (if created) to prefer audit schema.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'svc_audit_rw') THEN
    EXECUTE 'ALTER ROLE svc_audit_rw IN DATABASE sg SET search_path = audit, public';
  END IF;
END$$;
