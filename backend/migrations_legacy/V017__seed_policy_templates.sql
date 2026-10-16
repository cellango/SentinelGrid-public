-- Migration: Seed Policy Templates
-- Date: 2025-12-01
-- Purpose: Add default policy templates for common IAM scenarios

-- Sign-on Policy Templates

-- 1. Secure Admin Sign-on
INSERT INTO policy_templates (name, display_name, description, policy_type, template_data, is_system, category)
VALUES (
    'secure-admin-signon',
    'Secure Admin Sign-on',
    'Requires strong MFA (WebAuthn) for admin users, blocks high-risk countries',
    'signon',
    '{
        "id": "secure-admin-signon",
        "type": "signon",
        "scope": "tenant",
        "rules": [
            {
                "id": "rule_admin_high_risk",
                "name": "Admin High Risk Block",
                "description": "Block admin logins from high-risk countries",
                "conditions": [
                    {"type": "role", "op": "includes", "value": "TENANT_ADMIN"},
                    {"type": "risk_level", "op": "in", "value": ["high", "critical"]}
                ],
                "actions": [
                    {"type": "deny"},
                    {"type": "log", "level": "warn", "message": "High-risk admin sign-on attempt blocked"}
                ],
                "priority": 10
            },
            {
                "id": "rule_admin_require_webauthn",
                "name": "Admin Require WebAuthn",
                "description": "Require WebAuthn for all admin logins",
                "conditions": [
                    {"type": "role", "op": "includes", "value": "TENANT_ADMIN"}
                ],
                "actions": [
                    {"type": "require_factor", "value": "webauthn"},
                    {"type": "allow"}
                ],
                "priority": 20
            }
        ]
    }'::jsonb,
    true,
    'basic'
) ON CONFLICT DO NOTHING;

-- 2. Standard Employee Sign-on
INSERT INTO policy_templates (name, display_name, description, policy_type, template_data, is_system, category)
VALUES (
    'standard-employee-signon',
    'Standard Employee Sign-on',
    'Basic sign-on policy: require MFA for new devices, allow standard locations',
    'signon',
    '{
        "id": "standard-employee-signon",
        "type": "signon",
        "scope": "tenant",
        "rules": [
            {
                "id": "rule_new_device_mfa",
                "name": "New Device MFA",
                "description": "Require MFA for unknown devices",
                "conditions": [
                    {"type": "device_known", "op": "equals", "value": false}
                ],
                "actions": [
                    {"type": "require_factor", "value": "totp"},
                    {"type": "allow"}
                ],
                "priority": 10
            },
            {
                "id": "rule_standard_allow",
                "name": "Standard Allow",
                "description": "Allow standard employee sign-on",
                "conditions": [
                    {"type": "risk_level", "op": "in", "value": ["low", "medium"]}
                ],
                "actions": [
                    {"type": "allow"}
                ],
                "priority": 100
            }
        ]
    }'::jsonb,
    true,
    'basic'
) ON CONFLICT DO NOTHING;

-- Access Policy Templates

-- 3. Production Access Control
INSERT INTO policy_templates (name, display_name, description, policy_type, template_data, is_system, category)
VALUES (
    'production-access-control',
    'Production Access Control',
    'Restrict production access to specific teams, require approvals for privileged roles',
    'access',
    '{
        "id": "production-access-control",
        "type": "access",
        "scope": "app",
        "rules": [
            {
                "id": "rule_prod_team_only",
                "name": "Production Team Only",
                "description": "Only production team members can access",
                "conditions": [
                    {"type": "department", "op": "equals", "value": "Engineering"},
                    {"type": "group", "op": "includes", "value": "prod-ops"}
                ],
                "actions": [
                    {"type": "allow"}
                ],
                "priority": 10
            },
            {
                "id": "rule_privileged_approval",
                "name": "Privileged Role Approval",
                "description": "Require approval for privileged roles",
                "conditions": [
                    {"type": "entitlement", "op": "includes", "value": "privileged"}
                ],
                "actions": [
                    {"type": "require_approval", "approvers": ["manager", "app_owner"]},
                    {"type": "allow"}
                ],
                "priority": 20
            }
        ]
    }'::jsonb,
    true,
    'basic'
) ON CONFLICT DO NOTHING;

-- 4. Developer Access Policy
INSERT INTO policy_templates (name, display_name, description, policy_type, template_data, is_system, category)
VALUES (
    'developer-access-policy',
    'Developer Access Policy',
    'Allow developers access to staging, require approval for production',
    'access',
    '{
        "id": "developer-access-policy",
        "type": "access",
        "scope": "app",
        "rules": [
            {
                "id": "rule_staging_auto_approve",
                "name": "Staging Auto-approve",
                "description": "Auto-approve developer access to staging",
                "conditions": [
                    {"type": "role", "op": "includes", "value": "developer"},
                    {"type": "resource", "op": "contains", "value": "staging"}
                ],
                "actions": [
                    {"type": "auto_approve"},
                    {"type": "allow"}
                ],
                "priority": 10
            },
            {
                "id": "rule_prod_require_approval",
                "name": "Production Require Approval",
                "description": "Require manager approval for production access",
                "conditions": [
                    {"type": "role", "op": "includes", "value": "developer"},
                    {"type": "resource", "op": "contains", "value": "production"}
                ],
                "actions": [
                    {"type": "require_approval", "approvers": ["manager"]},
                    {"type": "allow"}
                ],
                "priority": 20
            }
        ]
    }'::jsonb,
    true,
    'basic'
) ON CONFLICT DO NOTHING;

-- Approval Policy Templates

-- 5. Privileged Access Approval
INSERT INTO policy_templates (name, display_name, description, policy_type, template_data, is_system, category)
VALUES (
    'privileged-access-approval',
    'Privileged Access Approval',
    'Require manager and security approval for privileged access, auto-expire after 4 hours',
    'approval',
    '{
        "id": "privileged-access-approval",
        "type": "approval",
        "scope": "tenant",
        "rules": [
            {
                "id": "rule_privileged_dual_approval",
                "name": "Dual Approval Required",
                "description": "Require manager and security team approval",
                "conditions": [
                    {"type": "entitlement", "op": "includes", "value": "privileged"}
                ],
                "actions": [
                    {"type": "require_approval", "approvers": ["manager", "security"]},
                    {"type": "set_expiry", "hours": 4},
                    {"type": "allow"}
                ],
                "priority": 10
            }
        ]
    }'::jsonb,
    true,
    'basic'
) ON CONFLICT DO NOTHING;

-- 6. Temporary Access Approval
INSERT INTO policy_templates (name, display_name, description, policy_type, template_data, is_system, category)
VALUES (
    'temporary-access-approval',
    'Temporary Access Approval',
    'Manager approval for temporary access, auto-expire after 8 hours',
    'approval',
    '{
        "id": "temporary-access-approval",
        "type": "approval",
        "scope": "tenant",
        "rules": [
            {
                "id": "rule_temporary_manager_approval",
                "name": "Manager Approval",
                "description": "Require manager approval for temporary access",
                "conditions": [
                    {"type": "request_duration", "op": "less_than", "value": 24}
                ],
                "actions": [
                    {"type": "require_approval", "approvers": ["manager"]},
                    {"type": "set_expiry", "hours": 8},
                    {"type": "allow"}
                ],
                "priority": 10
            }
        ]
    }'::jsonb,
    true,
    'basic'
) ON CONFLICT DO NOTHING;

-- SoD (Separation of Duties) Policy Templates

-- 7. Finance SoD Policy
INSERT INTO policy_templates (name, display_name, description, policy_type, template_data, is_system, category)
VALUES (
    'finance-sod-policy',
    'Finance SoD Policy',
    'Prevent users from having both Requester and Approver roles in finance system',
    'sod',
    '{
        "id": "finance-sod-policy",
        "type": "sod",
        "scope": "app",
        "rules": [
            {
                "id": "rule_finance_sod",
                "name": "Finance Requester/Approver SoD",
                "description": "Cannot have both requester and approver roles",
                "conditions": [
                    {"type": "entitlement", "op": "includes", "value": "finance:requester"},
                    {"type": "entitlement", "op": "includes", "value": "finance:approver"}
                ],
                "actions": [
                    {"type": "deny"},
                    {"type": "log", "level": "error", "message": "SoD violation: Cannot have both requester and approver roles"}
                ],
                "priority": 10
            }
        ]
    }'::jsonb,
    true,
    'compliance'
) ON CONFLICT DO NOTHING;

-- 8. Self-Approval Prevention
INSERT INTO policy_templates (name, display_name, description, policy_type, template_data, is_system, category)
VALUES (
    'self-approval-prevention',
    'Self-Approval Prevention',
    'Prevent users from approving their own access requests',
    'sod',
    '{
        "id": "self-approval-prevention",
        "type": "sod",
        "scope": "tenant",
        "rules": [
            {
                "id": "rule_no_self_approval",
                "name": "No Self-Approval",
                "description": "Users cannot approve their own requests",
                "conditions": [
                    {"type": "requester_id", "op": "equals", "field": "approver_id"}
                ],
                "actions": [
                    {"type": "deny"},
                    {"type": "log", "level": "warn", "message": "Self-approval attempt blocked"}
                ],
                "priority": 10
            }
        ]
    }'::jsonb,
    true,
    'compliance'
) ON CONFLICT DO NOTHING;

