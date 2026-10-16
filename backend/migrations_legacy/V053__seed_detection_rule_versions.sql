-- Backfill detection_rule_versions v1 for all detection_rules in system tenant

DO $$
DECLARE
    sys UUID := '00000000-0000-0000-0000-000000000000';
BEGIN
    INSERT INTO detection_rule_versions (
        rule_id, version, index_pattern, query, trigger_condition, severity, action_config, metadata
    )
    SELECT d.id,
           'v1',
           'alerts-*',
           '{"match_all":{}}'::jsonb,
           '{"type":"threshold","threshold":1}'::jsonb,
           COALESCE(drv.severity, 'medium'),
           '{}'::jsonb,
           COALESCE(drv.metadata, '{}'::jsonb)
    FROM detection_rules d
    LEFT JOIN detection_rule_versions drv ON drv.rule_id = d.id AND drv.version = 'v1'
    WHERE d.tenant_id = sys
      AND drv.rule_id IS NULL;
END $$;
