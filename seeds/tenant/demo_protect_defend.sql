-- Demo Protect+Defend tenant seed (idempotent)
-- Plan tier: protect_defend

BEGIN;

-- Ensure tenant exists (reuse legacy demo2 slug/id)
DO $$
DECLARE
    tenant_id UUID := 'b210c499-ea35-4e15-8b93-cd2446361d27';
    cust_id UUID := '423391f0-b46a-4ad3-b4eb-eb34a7bba5a3';
BEGIN
    -- Ensure realm exists for FK
    INSERT INTO public.realms (id, realm_name, realm_type, region, shard_number, tenant_count, max_tenants, status)
    VALUES (uuid_generate_v4(), 'demo2', 'multi_tenant', 'us', 2, 0, NULL, 'active')
    ON CONFLICT (realm_name) DO NOTHING;

    INSERT INTO public.customers (id, name, slug, pricing_tier, region, status, plan_tier)
    VALUES (cust_id, 'Demo Customer (Defend)', 'demo_defend', 'enterprise', 'us', 'active', 'protect_defend')
    ON CONFLICT (id) DO UPDATE
    SET name = EXCLUDED.name,
        slug = EXCLUDED.slug,
        pricing_tier = EXCLUDED.pricing_tier,
        plan_tier = EXCLUDED.plan_tier,
        status = EXCLUDED.status,
        updated_at = now();

    INSERT INTO public.tenants (id, name, slug, plan_tier, status, customer_id)
    VALUES (tenant_id, 'Demo Protect+Defend', 'demo2', 'protect_defend', 'active', cust_id)
    ON CONFLICT (slug) DO UPDATE
    SET name = EXCLUDED.name,
        plan_tier = EXCLUDED.plan_tier,
        status = EXCLUDED.status,
        customer_id = cust_id,
        realm_name = 'demo2',
        updated_at = now();

    UPDATE customers
    SET plan_tier = 'protect_defend'
    WHERE id IN (SELECT customer_id FROM tenants WHERE slug = 'demo2');
END $$;

-- Personas / users / role bindings (Admin/Analyst/Reviewer as appropriate)
DO $$
DECLARE
    t UUID;
    app_id UUID := '137401dd-154f-4729-a748-9f5e8b3eaadd';
    ent_admin UUID := 'da56e2cb-5db5-4cf9-a491-bf08c6ee183a';
    ent_analyst UUID := '1b12b0fc-7f89-4917-b86e-a9f49172cfda';
    ent_ops UUID := '18a0b506-8bae-4fa2-8711-16e88f055664';
    ut_admin UUID := '5aa23c2b-bacf-4b9e-81b0-6da2456f818c';
    ut_analyst UUID := 'cd22df7f-1d54-44f0-9c82-db0bc6611bd0';
    ut_ops UUID := '507634b1-bc77-4680-bbd8-ec5c7aab6324';
BEGIN
    SELECT id INTO t FROM tenants WHERE slug = 'demo2' LIMIT 1;
    IF t IS NULL THEN
        RAISE NOTICE 'demo2 tenant not found; skipping personas';
        RETURN;
    END IF;

    INSERT INTO public.apps (id, tenant_id, name, display_name, description, app_type, is_active, config)
    VALUES (app_id, t, 'iam-portal', 'IAM Portal', 'Portal app used for demo personas', 'internal', true, '{}'::jsonb)
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO public.entitlements (id, tenant_id, app_id, name, display_name, description, entitlement_type, is_privileged, requires_mfa, risk_level)
    VALUES
        (ent_admin, t, app_id, 'admin', 'Administrator', 'Full admin access for demo2', 'role', true, true, 'high'),
        (ent_analyst, t, app_id, 'analyst', 'Analyst', 'Analyst access for detections/alerts', 'role', false, false, 'medium'),
        (ent_ops, t, app_id, 'secops', 'SecOps Operator', 'Operator access for playbooks/incidents', 'role', false, false, 'medium')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO public.user_tenants (id, user_id, tenant_id, customer_id, realm_name)
    VALUES
        (ut_admin, 'demo2-admin', t, (SELECT customer_id FROM tenants WHERE id = t), 'demo2'),
        (ut_analyst, 'demo2-analyst', t, (SELECT customer_id FROM tenants WHERE id = t), 'demo2'),
        (ut_ops, 'demo2-ops', t, (SELECT customer_id FROM tenants WHERE id = t), 'demo2')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO public.user_entitlements (tenant_id, user_id, entitlement_id, granted_by)
    VALUES
        (t, 'demo2-admin', ent_admin, 'seed'),
        (t, 'demo2-analyst', ent_analyst, 'seed'),
        (t, 'demo2-ops', ent_ops, 'seed')
    ON CONFLICT DO NOTHING;
END $$;

-- IAM apps, access profiles, and devices for demo2
DO $$
DECLARE
    t UUID;
    cust UUID;
    org_sec UUID := '2e15d682-7ec4-4e5b-9b65-62c9a375262c';
    org_it UUID := 'b5fbe566-14b0-4a97-9d44-61d84145ba43';
    app_google UUID := '0be32917-0463-4c4c-b46e-dac50c2dc0ef';
    app_aws UUID := '2c3a1b0a-5610-4a87-8c83-5b9f2b83f131';
    app_jira UUID := '5a54ea3c-ddeb-4386-86bb-0f3154372317';
    ent_gsuite_admin UUID := 'b2be4b30-07ae-428f-8089-377f407e1fa2';
    ent_gsuite_user UUID := 'a5490fb0-b949-469e-bce1-5a3a52a77357';
    ent_aws_admin UUID := '6e442894-62b8-4a08-8329-2f1a7e427a76';
    ent_aws_view UUID := '8c0fe6f7-3a1d-4f4b-84d6-60aaf7d3909a';
    ent_jira_admin UUID := 'fcf8f0b8-050d-4a0a-9f1f-13d544c01161';
    ent_jira_user UUID := '5b3a4b8f-0ac0-42fa-8b3a-1e3ac097a51a';
    ap_standard UUID := '49ab0879-4845-4c48-b37d-6e31c4180a61';
    ap_secops UUID := 'a53a89b5-5ca0-4eb4-9a5e-c6b4f1b5c6db';
BEGIN
    SELECT id, customer_id INTO t, cust FROM tenants WHERE slug = 'demo2' LIMIT 1;
    IF t IS NULL THEN
        RAISE NOTICE 'demo2 tenant not found; skipping IAM apps/devices';
        RETURN;
    END IF;

    INSERT INTO public.organizations (id, customer_id, name, slug, realm_name, org_type, status)
    VALUES
        (org_sec, cust, 'Security Operations', 'demo2-secops', 'demo2', 'team', 'active'),
        (org_it, cust, 'IT Operations', 'demo2-it', 'demo2', 'team', 'active')
    ON CONFLICT (id) DO UPDATE
    SET name = EXCLUDED.name,
        slug = EXCLUDED.slug,
        org_type = EXCLUDED.org_type,
        status = EXCLUDED.status,
        updated_at = now();

    UPDATE public.user_tenants
    SET organization_id = org_sec
    WHERE tenant_id = t AND user_id IN ('demo2-admin','demo2-analyst','demo2-ops');
    UPDATE public.user_tenants
    SET organization_id = org_it
    WHERE tenant_id = t AND user_id = 'demo2-ops';

    INSERT INTO public.apps (id, tenant_id, name, display_name, description, app_type, icon_url, is_active, config)
    VALUES
        (app_google, t, 'google-workspace', 'Google Workspace', 'SSO for Workspace users', 'saml', 'https://logo.clearbit.com/google.com', true, '{"protocol":"saml","redirect_uris":["https://workspace.demo2"]}'::jsonb),
        (app_aws, t, 'aws', 'AWS Sandbox', 'Role-based access into AWS', 'oidc', 'https://logo.clearbit.com/aws.amazon.com', true, '{"protocol":"oidc","redirect_uris":["https://signin.aws.amazon.com/saml"]}'::jsonb),
        (app_jira, t, 'jira', 'Jira Cloud', 'Ticketing for SecOps', 'saml', 'https://logo.clearbit.com/atlassian.com', true, '{"protocol":"saml","redirect_uris":["https://demo2.atlassian.net"]}'::jsonb)
    ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name, description = EXCLUDED.description, config = EXCLUDED.config, icon_url = EXCLUDED.icon_url, is_active = EXCLUDED.is_active;

    INSERT INTO public.entitlements (id, tenant_id, app_id, name, display_name, description, entitlement_type, is_privileged, requires_mfa, risk_level)
    VALUES
        (ent_gsuite_admin, t, app_google, 'workspace-admin', 'Workspace Admin', 'Admin for Google Workspace', 'role', true, true, 'high'),
        (ent_gsuite_user, t, app_google, 'workspace-user', 'Workspace User', 'Standard Workspace access', 'role', false, false, 'low'),
        (ent_aws_admin, t, app_aws, 'aws-admin', 'AWS Admin', 'Admin role in AWS', 'role', true, true, 'high'),
        (ent_aws_view, t, app_aws, 'aws-readonly', 'AWS ReadOnly', 'Read-only AWS access', 'role', false, false, 'medium'),
        (ent_jira_admin, t, app_jira, 'jira-admin', 'Jira Admin', 'Admin for Jira', 'role', true, true, 'medium'),
        (ent_jira_user, t, app_jira, 'jira-user', 'Jira User', 'Standard Jira access', 'role', false, false, 'low')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO public.access_profiles (id, tenant_id, name, display_name, description, is_default, is_system, is_birthright, scope)
    VALUES
        (ap_standard, t, 'standard-employee', 'Standard Employee', 'Baseline access', true, true, true, 'all_users'),
        (ap_secops, t, 'secops-analyst', 'SecOps Analyst', 'Access for SOC analysts', false, false, false, 'team')
    ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, display_name = EXCLUDED.display_name, description = EXCLUDED.description, is_default = EXCLUDED.is_default, is_birthright = EXCLUDED.is_birthright, scope = EXCLUDED.scope;

    DELETE FROM public.access_profile_entitlements WHERE access_profile_id IN (ap_standard, ap_secops);
    INSERT INTO public.access_profile_entitlements (access_profile_id, entitlement_id)
    VALUES
        (ap_standard, ent_gsuite_user),
        (ap_standard, ent_jira_user),
        (ap_secops, ent_gsuite_user),
        (ap_secops, ent_aws_view),
        (ap_secops, ent_jira_user)
    ON CONFLICT DO NOTHING;

    DELETE FROM public.user_entitlements
    WHERE tenant_id = t
      AND user_id IN ('demo2-admin','demo2-analyst','demo2-ops')
      AND entitlement_id IN (ent_gsuite_admin, ent_gsuite_user, ent_aws_admin, ent_aws_view, ent_jira_admin, ent_jira_user);

    INSERT INTO public.user_entitlements (tenant_id, user_id, entitlement_id, granted_by)
    VALUES
        (t, 'demo2-admin', ent_gsuite_admin, 'seed'),
        (t, 'demo2-admin', ent_aws_admin, 'seed'),
        (t, 'demo2-admin', ent_jira_admin, 'seed'),
        (t, 'demo2-analyst', ent_gsuite_user, 'seed'),
        (t, 'demo2-analyst', ent_aws_view, 'seed'),
        (t, 'demo2-analyst', ent_jira_user, 'seed'),
        (t, 'demo2-ops', ent_gsuite_user, 'seed'),
        (t, 'demo2-ops', ent_aws_view, 'seed'),
        (t, 'demo2-ops', ent_jira_user, 'seed')
    ON CONFLICT DO NOTHING;

    DELETE FROM public.assets WHERE tenant_id = t AND asset_id IN ('demo2-laptop-01','demo2-laptop-02');
    INSERT INTO public.assets (tenant_id, asset_id, asset_type, name, hostname, operating_system, os_version, ip_address, owner, user_id, department, compliance_status, metadata, last_seen_at)
    VALUES
        (t, 'demo2-laptop-01', 'laptop', 'SOC Analyst Laptop', 'demo2-win-01', 'Windows', '11.0', '10.0.1.10', 'demo2-analyst@demo.sentinelgrid.ai', 'demo2-analyst', 'Security', 'compliant',
            '{"trust_status":"trusted","security_posture":{"score":86,"signals":{"disk_encrypted":true,"av_installed":true,"os_patch_level":"current"}}}'::jsonb, now() - interval '15 minutes'),
        (t, 'demo2-laptop-02', 'laptop', 'SecOps Operator Mac', 'demo2-mac-01', 'macOS', '14.3', '10.0.1.11', 'demo2-ops@demo.sentinelgrid.ai', 'demo2-ops', 'Security', 'compliant',
            '{"trust_status":"trusted","security_posture":{"score":89,"signals":{"disk_encrypted":true,"firewall_enabled":true}}}'::jsonb, now() - interval '40 minutes');
END $$;

-- Tenant IAM policy
DO $$
DECLARE
    t UUID;
BEGIN
    SELECT id INTO t FROM tenants WHERE slug = 'demo2' LIMIT 1;
    IF t IS NULL THEN
        RAISE NOTICE 'demo2 tenant not found; skipping policies';
        RETURN;
    END IF;

    INSERT INTO policies (id, tenant_id, name, display_name, description, policy_type, scope, scope_id, policy_data, is_active, priority, created_by, created_at, updated_at)
    VALUES (
        'ce1fac1f-39d0-4ac4-9efb-e574d2ff4acf',
        t,
        'demo2-authz-tenant-baseline',
        'Demo2 Tenant Baseline',
        'Baseline tenant policy allowing admins, secops, and analysts.',
        'authorization',
        'tenant',
        NULL,
        '{"rules":[{"id":"allow-core-roles","conditions":[{"attribute":"role","operator":"in","value":["admin","secops","analyst"]}],"actions":["allow"]}]}'::jsonb,
        TRUE,
        100,
        'seed',
        now(),
        now()
    )
    ON CONFLICT (id) DO NOTHING;
END $$;

-- Sample alerts for demo2
DO $$
DECLARE
    t UUID;
    now_ts TIMESTAMPTZ := now();
BEGIN
    SELECT id INTO t FROM tenants WHERE slug = 'demo2' LIMIT 1;
    IF t IS NULL THEN
        RAISE NOTICE 'demo2 tenant not found; skipping alerts';
        RETURN;
    END IF;

    INSERT INTO security_ops.alerts (id, tenant_id, source, external_id, title, description, raw_severity, status, detection_time, asset_id, user_identifier, raw_payload, nist_controls, mitre_tactics, mitre_techniques)
    VALUES
        ('cdf7a431-8278-4a9d-95d6-5573c3faf53d', t, 'iam', 'ALRT-DEMO2-001', 'Privileged role granted off-hours', 'Privileged group change outside approved window.', 'high', 'open', now_ts - interval '45 minutes', 'aws-demo-2', 'demo2-admin', '{"rule":"ID-PRIV-GROUP-OFFHRS"}', '["PR.AC"]'::jsonb, '["TA0003"]'::jsonb, '["T1098"]'::jsonb),
        ('03113ba6-2311-4416-a078-de18a4301c2b', t, 'siem', 'ALRT-DEMO2-002', 'Suspicious DNS pattern', 'Possible DGA/tunnel-like DNS traffic observed.', 'medium', 'open', now_ts - interval '3 hours', 'device-demo-02', NULL, '{"rule":"NW-SUSPICIOUS-DNS"}', '["DE.CM"]'::jsonb, '["TA0011"]'::jsonb, '["T1071.004"]'::jsonb),
        ('9a2e3c08-6798-40c3-9297-a6c9109cbf9a', t, 'cloudtrail', 'ALRT-DEMO2-003', 'KMS key disabled', 'KMS key disable detected in prod account.', 'high', 'open', now_ts - interval '1 day', 'aws-demo-2', NULL, '{"rule":"CLD-KMS-KEY-DISABLE-DELETE"}', '["PR.DS"]'::jsonb, '["TA0040"]'::jsonb, '["T1485"]'::jsonb)
    ON CONFLICT (id) DO NOTHING;
END $$;

-- Defend sample data (mirrors V007 style but scoped to demo2)
DO $$
DECLARE
    t UUID;
    now_ts TIMESTAMPTZ := now();
    scan_cloud UUID := 'ac9405f0-6c1b-4ecd-abe9-9bcb48600b3a';
    scan_trivy UUID := 'bc40b4a3-7ee1-4c7e-a270-c145a5b75d63';
    scan_git UUID := 'e066d6bd-fa35-4be4-a74f-9087b7b0b0a0';
    scan_zap UUID := '4dd4c777-01a0-4076-ad07-8dbcba5fd867';
    fg_cloud UUID := 'e183b13f-f1d5-4519-97ef-65f3f74096bb';
    fg_trivy UUID := 'd33da393-6efa-457c-b8c4-fdf9b2237ff9';
    fg_git UUID := '096f5be2-821f-4585-9a16-043e2d75dba2';
    fg_zap UUID := 'eea95a21-ea71-47d9-9d52-1b4dcbe19399';
BEGIN
    SELECT id INTO t FROM tenants WHERE slug = 'demo2' LIMIT 1;
    IF t IS NULL THEN
        RAISE NOTICE 'demo2 tenant not found; skipping defend seeds';
        RETURN;
    END IF;

    -- Clear existing scans for idempotency (orchestration schema + public mirror)
    DELETE FROM orchestration.scans WHERE tenant_id = t;
    DELETE FROM scans WHERE tenant_id = t;

    INSERT INTO orchestration.scans (id, tenant_id, scanner_id, target_ref, status, created_at, updated_at, started_at, finished_at, summary)
    VALUES
        (scan_cloud, t, 'cloud', 'aws-demo-2', 'completed', now_ts, now_ts, now_ts - INTERVAL '45 minutes', now_ts - INTERVAL '40 minutes', '{"findings":3,"severity":"medium"}'),
        (scan_trivy, t, 'trivy', 'device-demo-02', 'completed', now_ts, now_ts, now_ts - INTERVAL '90 minutes', now_ts - INTERVAL '84 minutes', '{"findings":4,"severity":"high","type":"vulnerability","target_kind":"device"}'),
        (scan_git, t, 'git', 'github/demo2/repo', 'completed', now_ts, now_ts, now_ts - INTERVAL '2 hours 15 minutes', now_ts - INTERVAL '2 hours 5 minutes', '{"findings":1,"severity":"low"}'),
        (scan_zap, t, 'zap', 'https://demo2.app/login', 'completed', now_ts, now_ts, now_ts - INTERVAL '3 hours 10 minutes', now_ts - INTERVAL '2 hours 55 minutes', '{"findings":2,"severity":"medium","type":"vulnerability","target_kind":"app"}')
    ON CONFLICT (id) DO NOTHING;

    -- Mirror scans into public.scans to satisfy fix_group FK
    INSERT INTO scans (id, tenant_id, scanner_id, target_ref, status, created_at, updated_at, started_at, finished_at, summary)
    VALUES
        (scan_cloud, t, 'cloud', 'aws-demo-2', 'completed', now_ts, now_ts, now_ts - INTERVAL '45 minutes', now_ts - INTERVAL '40 minutes', '{"findings":3,"severity":"medium"}'),
        (scan_trivy, t, 'trivy', 'device-demo-02', 'completed', now_ts, now_ts, now_ts - INTERVAL '90 minutes', now_ts - INTERVAL '84 minutes', '{"findings":4,"severity":"high","type":"vulnerability","target_kind":"device"}'),
        (scan_git, t, 'git', 'github/demo2/repo', 'completed', now_ts, now_ts, now_ts - INTERVAL '2 hours 15 minutes', now_ts - INTERVAL '2 hours 5 minutes', '{"findings":1,"severity":"low"}'),
        (scan_zap, t, 'zap', 'https://demo2.app/login', 'completed', now_ts, now_ts, now_ts - INTERVAL '3 hours 10 minutes', now_ts - INTERVAL '2 hours 55 minutes', '{"findings":2,"severity":"medium","type":"vulnerability","target_kind":"app"}')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO fix_groups (id, tenant_id, scan_id, type, description, fixed_in_target, priority, sla_due, status, created_at, updated_at, ai_guidance, ticket_id, ticket_status)
    VALUES
        (fg_cloud, t, scan_cloud, 'patch_group', 'Apply cloud patches for aws-demo-2', NULL, 'P1', now_ts + INTERVAL '7 days', 'open', now_ts, now_ts,
            '{"summary":"Apply cloud patches for aws-demo-2","steps":["Review failing controls","Apply vendor patches","Re-run the scan"],"validation":["Re-run the originating scan"]}', NULL, NULL),
        (fg_trivy, t, scan_trivy, 'dependency_upgrade', 'Rebuild base image for device-demo-02', 'base:2024.01', 'P0', now_ts + INTERVAL '72 hours', 'open', now_ts, now_ts,
            '{"summary":"Upgrade dependencies/base image for device-demo-02","steps":["Identify vulnerable packages","Rebuild image with patched base","Re-run scan and smoke tests"],"validation":["Re-run the originating scan"]}', 'TKT-DEMO2-1', 'open'),
        (fg_git, t, scan_git, 'dependency_upgrade', 'Review repo findings for github/demo2/repo', NULL, 'P2', now_ts + INTERVAL '30 days', 'open', now_ts, now_ts,
            '{"summary":"Address repo findings","steps":["Fix SAST/secret issues","Run CI security scans","Re-run scan"],"validation":["Re-run the originating scan"]}', NULL, NULL),
        (fg_zap, t, scan_zap, 'dependency_upgrade', 'Fix web findings for demo2 app login', NULL, 'P2', now_ts + INTERVAL '30 days', 'open', now_ts, now_ts,
            '{"summary":"Fix web vulns for demo2 app login","steps":["Review ZAP findings","Patch/mitigate vulnerable routes","Re-run DAST"],"validation":["Re-run the originating scan"]}', NULL, NULL)
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO fix_group_assets (fix_group_id, tenant_id, asset_ref, asset_type)
    VALUES
        (fg_cloud, t, 'aws-demo-2', 'cloud'),
        (fg_trivy, t, 'device-demo-02', 'trivy'),
        (fg_git, t, 'github/demo2/repo', 'git'),
        (fg_zap, t, 'https://demo2.app/login', 'zap')
    ON CONFLICT (fix_group_id, asset_ref) DO NOTHING;

    INSERT INTO fix_group_cves (fix_group_id, tenant_id, cve_id)
    VALUES
        (fg_cloud, t, 'CVE-2024-1234'),
        (fg_trivy, t, 'CVE-2024-5678'),
        (fg_trivy, t, 'CVE-2023-9999'),
        (fg_zap, t, 'CVE-2022-5555')
    ON CONFLICT (fix_group_id, cve_id) DO NOTHING;
END $$;

COMMIT;
