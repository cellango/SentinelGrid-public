-- Migration: 044 - Seed Policy Templates
-- Purpose: Provide starter IAM policy templates for the no-code policy builder.

-- Seed three common templates (idempotent)
WITH templates AS (
    SELECT * FROM (VALUES
        (
            'business_hours_admin',
            'Business Hours Admin Access',
            'Admin access allowed only during business hours (UTC)',
            'access',
            jsonb_build_object(
                'id', 'policy-business-hours-admin',
                'type', 'access',
                'rules', jsonb_build_array(
                    jsonb_build_object(
                        'id', 'rule-business-hours',
                        'name', 'Business hours only',
                        'priority', 100,
                        'is_active', true,
                        'conditions', jsonb_build_array(
                            jsonb_build_object(
                                'type', 'time',
                                'op', 'between',
                                'value', jsonb_build_object(
                                    'start', '09:00',
                                    'end', '17:00',
                                    'timezone', 'UTC'
                                )
                            )
                        ),
                        'actions', jsonb_build_array(
                            jsonb_build_object('type', 'permit')
                        )
                    )
                )
            )
        ),
        (
            'office_ip_allow',
            'Office IP Allowlist',
            'Restrict access to approved office IP/CIDR ranges',
            'access',
            jsonb_build_object(
                'id', 'policy-office-ip',
                'type', 'access',
                'rules', jsonb_build_array(
                    jsonb_build_object(
                        'id', 'rule-office-ip',
                        'name', 'Office IP only',
                        'priority', 100,
                        'is_active', true,
                        'conditions', jsonb_build_array(
                            jsonb_build_object(
                                'type', 'ip',
                                'op', 'in_cidr',
                                'value', jsonb_build_array('203.0.113.0/24', '198.51.100.0/24')
                            )
                        ),
                        'actions', jsonb_build_array(
                            jsonb_build_object('type', 'permit')
                        )
                    )
                )
            )
        ),
        (
            'step_up_mfa',
            'Step-up MFA for High Risk',
            'Require MFA when risk is high or outside trusted context',
            'signon',
            jsonb_build_object(
                'id', 'policy-step-up-mfa',
                'type', 'signon',
                'rules', jsonb_build_array(
                    jsonb_build_object(
                        'id', 'rule-step-up',
                        'name', 'Step-up MFA on risk',
                        'priority', 100,
                        'is_active', true,
                        'conditions', jsonb_build_array(
                            jsonb_build_object(
                                'type', 'risk_score',
                                'op', 'gte',
                                'value', 70
                            )
                        ),
                        'actions', jsonb_build_array(
                            jsonb_build_object('type', 'require_mfa')
                        )
                    )
                )
            )
        )
    ) AS t(name, display_name, description, policy_type, template_data)
)
INSERT INTO policy_templates (id, name, display_name, description, policy_type, template_data, is_system, category)
SELECT
    gen_random_uuid(),
    t.name,
    t.display_name,
    t.description,
    t.policy_type,
    t.template_data,
    true,
    'starter'
FROM templates t
ON CONFLICT DO NOTHING;

-- Mark existing system templates as starter category if missing
UPDATE policy_templates
SET category = COALESCE(category, 'starter')
WHERE is_system = true;
