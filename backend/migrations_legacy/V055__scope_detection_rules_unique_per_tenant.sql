-- Scope detection_rules uniqueness to (rule_key, tenant_id); keep built-in uniqueness

DO $$
BEGIN
    -- Drop the existing unique constraint on rule_key
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'detection_rules_rule_key_key'
          AND conrelid = 'detection_rules'::regclass
    ) THEN
        ALTER TABLE detection_rules DROP CONSTRAINT detection_rules_rule_key_key;
    END IF;

    -- Add composite unique on (rule_key, tenant_id)
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'detection_rules_rule_key_tenant_uniq'
          AND conrelid = 'detection_rules'::regclass
    ) THEN
        ALTER TABLE detection_rules
        ADD CONSTRAINT detection_rules_rule_key_tenant_uniq UNIQUE (rule_key, tenant_id);
    END IF;

    -- Optional: enforce unique rule_key for built-ins across all tenants
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'detection_rules_rule_key_builtin_uniq'
          AND tablename = 'detection_rules'
    ) THEN
        CREATE UNIQUE INDEX detection_rules_rule_key_builtin_uniq
            ON detection_rules(rule_key)
            WHERE is_builtin = true;
    END IF;
END $$;
