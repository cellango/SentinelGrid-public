-- Promote system-tenant playbooks to built-ins now that the master pseudo-tenant is removed.

DO $$
DECLARE
    sys UUID := '9c7df7a9-5a0b-4412-a41c-0c0ea777b2f0';
BEGIN
    UPDATE playbooks
    SET is_builtin = TRUE
    WHERE tenant_id = sys;
END $$;
