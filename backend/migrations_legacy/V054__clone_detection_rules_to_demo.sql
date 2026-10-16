-- Clone detection_rules and detection_rule_versions from system tenant to demo tenant
-- System tenant: 00000000-0000-0000-0000-000000000000
-- Demo tenant:    c6d82f67-36f1-4c7e-af66-d1333e45cde7

DO $$
DECLARE
    sys  UUID := '00000000-0000-0000-0000-000000000000';
    demo UUID := 'c6d82f67-36f1-4c7e-af66-d1333e45cde7';
BEGIN
    -- Clone detection_rules
    WITH src AS (
        SELECT rule_key, name, description, category, current_version, is_builtin
        FROM detection_rules
        WHERE tenant_id = sys
    )
    INSERT INTO detection_rules (rule_key, name, description, category, current_version, is_builtin, tenant_id)
    SELECT rule_key, name, description, category, current_version, is_builtin, demo
    FROM src
    ON CONFLICT (rule_key) DO NOTHING;

    -- Clone detection_rule_versions (all versions) using rule_key mapping
    WITH demo_rules AS (
        SELECT rule_key, id
        FROM detection_rules
        WHERE tenant_id = demo
    ),
    sys_versions AS (
        SELECT dr.rule_key, drv.version, drv.index_pattern, drv.query, drv.trigger_condition,
               drv.severity, drv.action_config, drv.metadata
        FROM detection_rules dr
        JOIN detection_rule_versions drv ON drv.rule_id = dr.id
        WHERE dr.tenant_id = sys
    )
    INSERT INTO detection_rule_versions (rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata)
    SELECT d.id, sv.version, sv.index_pattern, sv.query, sv.trigger_condition, sv.severity, sv.action_config, sv.metadata
    FROM sys_versions sv
    JOIN demo_rules d ON d.rule_key = sv.rule_key
    ON CONFLICT (rule_id, version) DO NOTHING;
END $$;
