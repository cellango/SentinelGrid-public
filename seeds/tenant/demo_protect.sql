-- Demo Protect tenant seed (idempotent)
-- Plan tier: protect

BEGIN;

-- Ensure tenant exists (new protect-only demo)
DO $$
DECLARE
    tenant_id UUID := 'e4eddd32-5042-44ab-8cfc-cd2c841b633d';
    cust_id UUID := '895e6576-c816-4887-9a8a-e02b8500c23a';
BEGIN
    -- Ensure realm exists for FK
    INSERT INTO public.realms (id, realm_name, realm_type, region, shard_number, tenant_count, max_tenants, status)
    VALUES (uuid_generate_v4(), 'demo_protect', 'multi_tenant', 'us', 3, 0, NULL, 'active')
    ON CONFLICT (realm_name) DO NOTHING;

    INSERT INTO public.customers (id, name, slug, pricing_tier, region, status, plan_tier)
    VALUES (cust_id, 'Demo Customer (Protect)', 'demo_protect_cust', 'starter', 'us', 'active', 'protect')
    ON CONFLICT (id) DO UPDATE
    SET name = EXCLUDED.name,
        slug = EXCLUDED.slug,
        pricing_tier = EXCLUDED.pricing_tier,
        plan_tier = EXCLUDED.plan_tier,
        status = EXCLUDED.status,
        updated_at = now();

    INSERT INTO public.tenants (id, name, slug, plan_tier, status, customer_id)
    VALUES (tenant_id, 'Demo Protect', 'demo_protect', 'protect', 'active', cust_id)
    ON CONFLICT (slug) DO UPDATE
    SET name = EXCLUDED.name,
        plan_tier = EXCLUDED.plan_tier,
        status = EXCLUDED.status,
        customer_id = cust_id,
        realm_name = 'demo_protect',
        updated_at = now();

    UPDATE customers
    SET plan_tier = 'protect'
    WHERE id IN (SELECT customer_id FROM tenants WHERE slug = 'demo_protect');
END $$;

-- Personas / users / role bindings for Protect (add actual user/role IDs as available)
DO $$
DECLARE
    t UUID;
    app_id UUID := 'ed640a44-ee31-4267-92bd-c07ac701cccc';
    ent_admin UUID := '9b691406-e5d1-43ef-85e3-07983ad933af';
    ent_viewer UUID := 'b50eec9c-5bef-4822-8ed2-a3917906e0c5';
    ut_admin UUID := 'ffe248a4-9cf0-4db1-b4b7-4d4196e505fa';
    ut_viewer UUID := 'e6123c87-1d03-48cc-ad1b-f2b74d5d84f3';
BEGIN
    SELECT id INTO t FROM tenants WHERE slug = 'demo_protect' LIMIT 1;
    IF t IS NULL THEN
        RAISE NOTICE 'demo_protect tenant not found; skipping personas';
        RETURN;
    END IF;

    INSERT INTO public.apps (id, tenant_id, name, display_name, description, app_type, is_active, config)
    VALUES (app_id, t, 'iam-portal', 'IAM Portal', 'Portal app used for demo personas', 'internal', true, '{}'::jsonb)
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO public.entitlements (id, tenant_id, app_id, name, display_name, description, entitlement_type, is_privileged, requires_mfa, risk_level)
    VALUES
        (ent_admin, t, app_id, 'admin', 'Administrator', 'Admin access for Protect tenant', 'role', true, true, 'high'),
        (ent_viewer, t, app_id, 'viewer', 'Viewer', 'Read-only access for Protect tenant', 'role', false, false, 'low')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO public.user_tenants (id, user_id, tenant_id, customer_id, realm_name)
    VALUES
        (ut_admin, 'demo-protect-admin', t, (SELECT customer_id FROM tenants WHERE id = t), 'demo_protect'),
        (ut_viewer, 'demo-protect-viewer', t, (SELECT customer_id FROM tenants WHERE id = t), 'demo_protect')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO public.user_entitlements (tenant_id, user_id, entitlement_id, granted_by)
    VALUES
        (t, 'demo-protect-admin', ent_admin, 'seed'),
        (t, 'demo-protect-viewer', ent_viewer, 'seed')
    ON CONFLICT DO NOTHING;
END $$;

-- IAM apps, access profiles, and devices for Protect-only tenant
DO $$
DECLARE
    t UUID;
    cust UUID;
    org_it UUID := '6c1d0fbb-783b-4f4d-8bf7-e0e2012bc7aa';
    org_hr UUID := 'c46b6c3c-9f2e-4b9d-bf2b-31f5ed8b0c94';
    app_google UUID := '6acb1b54-1382-4cf3-8a07-7597baa2d271';
    app_slack UUID := '1c2f9fd8-33bf-4c93-a62f-988af617eced';
    app_vpn UUID := 'a0ac3670-7d3e-4ca3-9bcd-7b8f6f5bdc0a';
    ent_gsuite_admin UUID := 'fa05c5f0-4a6d-4a28-8e25-9cb2c71d9f38';
    ent_gsuite_user UUID := '9cb4b3d7-0aa3-4b1c-9a73-d7c3afb48afc';
    ent_slack_admin UUID := 'cbb2e153-f22b-4ea1-9bee-61aaee74929e';
    ent_slack_user UUID := 'b64743c5-403d-4c99-9a76-e25905616a71';
    ent_vpn_user UUID := 'e5f6acbd-0f1a-4a65-9b6b-323d9f1cdbb1';
    ap_standard UUID := 'b8d29c54-2d8e-49e6-8c91-4384f7b0d3a2';
    ap_viewer UUID := 'f1de2874-91c9-4fd0-8f00-829b63f8eede';
BEGIN
    SELECT id, customer_id INTO t, cust FROM tenants WHERE slug = 'demo_protect' LIMIT 1;
    IF t IS NULL THEN
        RAISE NOTICE 'demo_protect tenant not found; skipping IAM apps/devices';
        RETURN;
    END IF;

    INSERT INTO public.organizations (id, customer_id, name, slug, realm_name, org_type, status)
    VALUES
        (org_it, cust, 'IT Operations', 'demo-protect-it', 'demo_protect', 'team', 'active'),
        (org_hr, cust, 'People Operations', 'demo-protect-hr', 'demo_protect', 'team', 'active')
    ON CONFLICT (id) DO UPDATE
    SET name = EXCLUDED.name,
        slug = EXCLUDED.slug,
        org_type = EXCLUDED.org_type,
        status = EXCLUDED.status,
        updated_at = now();

    UPDATE public.user_tenants
    SET organization_id = org_it
    WHERE tenant_id = t AND user_id = 'demo-protect-admin';
    UPDATE public.user_tenants
    SET organization_id = org_hr
    WHERE tenant_id = t AND user_id = 'demo-protect-viewer';

    INSERT INTO public.apps (id, tenant_id, name, display_name, description, app_type, icon_url, is_active, config)
    VALUES
        (app_google, t, 'google-workspace', 'Google Workspace', 'Workspace for demo protect', 'saml', 'https://logo.clearbit.com/google.com', true, '{"protocol":"saml","redirect_uris":["https://workspace.demo-protect"]}'::jsonb),
        (app_slack, t, 'slack', 'Slack', 'Messaging for protect tenant', 'saml', 'https://logo.clearbit.com/slack.com', true, '{"protocol":"saml","redirect_uris":["https://demo-protect.slack.com"]}'::jsonb),
        (app_vpn, t, 'vpn', 'Corporate VPN', 'VPN access profile', 'internal', NULL, true, '{"protocol":"custom","notes":"Demo VPN seed"}'::jsonb)
    ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name, description = EXCLUDED.description, config = EXCLUDED.config, is_active = EXCLUDED.is_active;

    INSERT INTO public.entitlements (id, tenant_id, app_id, name, display_name, description, entitlement_type, is_privileged, requires_mfa, risk_level)
    VALUES
        (ent_gsuite_admin, t, app_google, 'workspace-admin', 'Workspace Admin', 'Admin rights in Workspace', 'role', true, true, 'high'),
        (ent_gsuite_user, t, app_google, 'workspace-user', 'Workspace User', 'Standard Workspace access', 'role', false, false, 'low'),
        (ent_slack_admin, t, app_slack, 'slack-admin', 'Slack Admin', 'Admin in Slack', 'role', true, true, 'medium'),
        (ent_slack_user, t, app_slack, 'slack-user', 'Slack User', 'Standard Slack access', 'role', false, false, 'low'),
        (ent_vpn_user, t, app_vpn, 'vpn-user', 'VPN User', 'VPN access', 'role', false, true, 'medium')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO public.access_profiles (id, tenant_id, name, display_name, description, is_default, is_system, is_birthright, scope)
    VALUES
        (ap_standard, t, 'standard-employee', 'Standard Employee', 'Baseline access for all employees', true, true, true, 'all_users'),
        (ap_viewer, t, 'read-only', 'Read-only', 'Viewer profile for auditors', false, false, false, 'team')
    ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, display_name = EXCLUDED.display_name, description = EXCLUDED.description, is_default = EXCLUDED.is_default, is_birthright = EXCLUDED.is_birthright, scope = EXCLUDED.scope;

    DELETE FROM public.access_profile_entitlements WHERE access_profile_id IN (ap_standard, ap_viewer);
    INSERT INTO public.access_profile_entitlements (access_profile_id, entitlement_id)
    VALUES
        (ap_standard, ent_gsuite_user),
        (ap_standard, ent_slack_user),
        (ap_standard, ent_vpn_user),
        (ap_viewer, ent_gsuite_user),
        (ap_viewer, ent_slack_user)
    ON CONFLICT DO NOTHING;

    DELETE FROM public.user_entitlements
    WHERE tenant_id = t
      AND user_id IN ('demo-protect-admin','demo-protect-viewer')
      AND entitlement_id IN (ent_gsuite_admin, ent_gsuite_user, ent_slack_admin, ent_slack_user, ent_vpn_user);

    INSERT INTO public.user_entitlements (tenant_id, user_id, entitlement_id, granted_by)
    VALUES
        (t, 'demo-protect-admin', ent_gsuite_admin, 'seed'),
        (t, 'demo-protect-admin', ent_slack_admin, 'seed'),
        (t, 'demo-protect-admin', ent_vpn_user, 'seed'),
        (t, 'demo-protect-viewer', ent_gsuite_user, 'seed'),
        (t, 'demo-protect-viewer', ent_slack_user, 'seed')
    ON CONFLICT DO NOTHING;

    DELETE FROM public.assets WHERE tenant_id = t AND asset_id IN ('demo-protect-laptop-01','demo-protect-laptop-02');
    INSERT INTO public.assets (tenant_id, asset_id, asset_type, name, hostname, operating_system, os_version, ip_address, owner, user_id, department, compliance_status, metadata, last_seen_at)
    VALUES
        (t, 'demo-protect-laptop-01', 'laptop', 'Admin Laptop', 'dp-mac-01', 'macOS', '14.3', '10.0.2.10', 'demo-protect-admin@demo.sentinelgrid.ai', 'demo-protect-admin', 'IT', 'compliant',
            '{"trust_status":"trusted","security_posture":{"score":91,"signals":{"disk_encrypted":true,"firewall_enabled":true}}}'::jsonb, now() - interval '10 minutes'),
        (t, 'demo-protect-laptop-02', 'laptop', 'Viewer Laptop', 'dp-win-01', 'Windows', '11', '10.0.2.11', 'demo-protect-viewer@demo.sentinelgrid.ai', 'demo-protect-viewer', 'People', 'compliant',
            '{"trust_status":"trusted","security_posture":{"score":87,"signals":{"disk_encrypted":true,"av_installed":true}}}'::jsonb, now() - interval '35 minutes');
END $$;

-- Protect-specific seeds (authz policies, minimal alerts)
DO $$
DECLARE
    t UUID;
BEGIN
    SELECT id INTO t FROM tenants WHERE slug = 'demo_protect' LIMIT 1;
    IF t IS NULL THEN
        RAISE NOTICE 'demo_protect tenant not found; skipping policies';
        RETURN;
    END IF;

    INSERT INTO policies (id, tenant_id, name, display_name, description, policy_type, scope, scope_id, policy_data, is_active, priority, created_by, created_at, updated_at)
    VALUES (
        'f16619ec-c387-44cf-b7c9-4e246ca4fc23',
        t,
        'demo-protect-authz-baseline',
        'Demo Protect Baseline',
        'Baseline tenant policy allowing admins and viewers',
        'authorization',
        'tenant',
        NULL,
        '{"rules":[{"id":"allow-core","conditions":[{"attribute":"role","operator":"in","value":["admin","viewer"]}],"actions":["allow"]}]}'::jsonb,
        TRUE,
        100,
        'seed',
        now(),
        now()
    )
    ON CONFLICT (id) DO NOTHING;
END $$;

-- Minimal alerts for Protect (for UI smoke)
DO $$
DECLARE
    t UUID;
    now_ts TIMESTAMPTZ := now();
BEGIN
    SELECT id INTO t FROM tenants WHERE slug = 'demo_protect' LIMIT 1;
    IF t IS NULL THEN
        RAISE NOTICE 'demo_protect tenant not found; skipping alerts';
        RETURN;
    END IF;

    INSERT INTO security_ops.alerts (id, tenant_id, source, external_id, title, description, raw_severity, status, detection_time, asset_id, user_identifier, raw_payload, nist_controls, mitre_tactics, mitre_techniques)
    VALUES
        ('ccd09dc1-1d2c-4487-8f3f-d2c7f5b79fbd', t, 'iam', 'ALRT-PROTECT-001', 'MFA disabled for user', 'User disabled MFA on their account.', 'high', 'open', now_ts - interval '2 hours', 'iam-portal', 'demo-protect-admin', '{"rule":"ID-MFA-DISABLED"}', '["PR.AC"]'::jsonb, '["TA0006"]'::jsonb, '["T1556"]'::jsonb),
        ('e1578536-5895-420f-a4b1-b7f937fb25ae', t, 'iam', 'ALRT-PROTECT-002', 'Failed login burst', 'Multiple failed logins detected for a single user.', 'medium', 'open', now_ts - interval '6 hours', 'iam-portal', 'demo-protect-viewer', '{"rule":"ID-FAILED-LOGIN-BURST"}', '["DE.CM"]'::jsonb, '["TA0006"]'::jsonb, '["T1110"]'::jsonb)
    ON CONFLICT (id) DO NOTHING;
END $$;

COMMIT;
