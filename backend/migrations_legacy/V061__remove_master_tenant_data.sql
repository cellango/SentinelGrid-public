-- Remove legacy master (all-zero UUID) tenant data now that the system tenant is the single platform home.
-- Safe to run multiple times.

DO $$
DECLARE
    master UUID := '00000000-0000-0000-0000-000000000000';
BEGIN
    -- Delete monitor bindings for master
    DELETE FROM tenant_detection_monitors WHERE tenant_id = master;

    -- Delete detection→playbook mappings for master
    DELETE FROM detection_playbook_mappings WHERE tenant_id = master;

    -- Delete detection bindings scoped to master
    DELETE FROM detection_bindings WHERE tenant_id = master;

    -- Delete detection rule versions/rules scoped to master (if any exist)
    DELETE FROM detection_rule_versions
    WHERE rule_id IN (SELECT id FROM detection_rules WHERE tenant_id = master);
    DELETE FROM detection_rules WHERE tenant_id = master;

    -- Delete master playbooks
    DELETE FROM playbooks WHERE tenant_id = master;
END $$;
