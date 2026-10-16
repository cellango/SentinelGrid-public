-- Demo Protect+Defend+Comply tenant seed (idempotent)
-- Plan tier: protect_defend_comply

BEGIN;

-- Ensure tenant exists (reuse legacy demo slug/id to avoid breaking references)
DO $$
DECLARE
    demo_id UUID := 'ff1c2b60-1fd6-46d1-8458-b0484f5d58f8';
    cust_id UUID := 'bc314740-48d4-4a2c-bb4a-c94d3808a448';
BEGIN
    -- Ensure realm exists for FK
    INSERT INTO public.realms (id, realm_name, realm_type, region, shard_number, tenant_count, max_tenants, status)
    VALUES (uuid_generate_v4(), 'demo', 'multi_tenant', 'us', 1, 0, NULL, 'active')
    ON CONFLICT (realm_name) DO NOTHING;

    INSERT INTO public.customers (id, name, slug, pricing_tier, region, status, plan_tier)
    VALUES (cust_id, 'Demo Customer (Full)', 'demo_full', 'enterprise', 'us', 'active', 'protect_defend_comply')
    ON CONFLICT (id) DO UPDATE
    SET name = EXCLUDED.name,
        slug = EXCLUDED.slug,
        pricing_tier = EXCLUDED.pricing_tier,
        plan_tier = EXCLUDED.plan_tier,
        status = EXCLUDED.status,
        updated_at = now();

    INSERT INTO public.tenants (id, name, slug, plan_tier, status, customer_id)
    VALUES (demo_id, 'Demo Protect+Defend+Comply', 'demo', 'protect_defend_comply', 'active', cust_id)
    ON CONFLICT (slug) DO UPDATE
    SET name = EXCLUDED.name,
        plan_tier = EXCLUDED.plan_tier,
        status = EXCLUDED.status,
        customer_id = cust_id,
        realm_name = 'demo',
        updated_at = now();

    UPDATE customers
    SET plan_tier = 'protect_defend_comply'
    WHERE id IN (SELECT customer_id FROM tenants WHERE slug = 'demo');
END $$;

-- Personas / users / role bindings (Admin/Analyst/Reviewer/Compliance roles as appropriate)
DO $$
DECLARE
    t UUID;
    app_id UUID := '1e74de6e-2ed1-44ef-bfd8-3faff1c3993b';
    ent_admin UUID := '46999b58-9479-4c3e-937a-b20adbb7fecb';
    ent_analyst UUID := '03773182-e45f-4e67-8365-6a0918952a61';
    ent_compliance UUID := '6548fa15-2756-4fee-8953-77e344b6dee5';
    ut_admin UUID := '45915479-9ef2-441c-93cf-07d865463f53';
    ut_analyst UUID := '73d92a8b-f9fc-4a72-bf79-1a97efd376da';
    ut_compliance UUID := 'eae71900-2b64-4a92-96fc-5ee72d636d1a';
BEGIN
    SELECT id INTO t FROM tenants WHERE slug = 'demo' LIMIT 1;
    IF t IS NULL THEN
        RAISE NOTICE 'demo tenant not found; skipping personas';
        RETURN;
    END IF;

    INSERT INTO public.apps (id, tenant_id, name, display_name, description, app_type, is_active, config)
    VALUES (app_id, t, 'iam-portal', 'IAM Portal', 'Portal app used for demo personas', 'internal', true, '{}'::jsonb)
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO public.entitlements (id, tenant_id, app_id, name, display_name, description, entitlement_type, is_privileged, requires_mfa, risk_level)
    VALUES
        (ent_admin, t, app_id, 'admin', 'Administrator', 'Full admin access for demo', 'role', true, true, 'high'),
        (ent_analyst, t, app_id, 'analyst', 'Analyst', 'Analyst access to detections/alerts', 'role', false, false, 'medium'),
        (ent_compliance, t, app_id, 'compliance', 'Compliance', 'Compliance/GRC access for reports', 'role', false, false, 'medium')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO public.user_tenants (id, user_id, tenant_id, customer_id, realm_name)
    VALUES
        (ut_admin, 'demo-admin', t, (SELECT customer_id FROM tenants WHERE id = t), 'demo'),
        (ut_analyst, 'demo-analyst', t, (SELECT customer_id FROM tenants WHERE id = t), 'demo'),
        (ut_compliance, 'demo-compliance', t, (SELECT customer_id FROM tenants WHERE id = t), 'demo')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO public.user_entitlements (tenant_id, user_id, entitlement_id, granted_by)
    VALUES
        (t, 'demo-admin', ent_admin, 'seed'),
        (t, 'demo-analyst', ent_analyst, 'seed'),
        (t, 'demo-compliance', ent_compliance, 'seed')
    ON CONFLICT DO NOTHING;
END $$;

-- IAM apps, access profiles, and devices (demo realm)
DO $$
DECLARE
    t UUID;
    cust UUID;
    -- org units / teams
    org_sec UUID := '8f23414c-2f2b-46e9-9cf3-6fb20c65e9d6';
    org_eng UUID := 'c2b223ce-14e7-4d02-a6c0-e7c2cbfa2d13';
    -- apps
    app_google UUID := '3f7c8f2e-2e4a-4f90-9e71-6ba4c4ecf5e2';
    app_aws UUID := 'c45f35f1-4d18-4b4f-95c5-6a7d29b6b1c2';
    app_jira UUID := 'b8b9836a-9b4d-4b95-9da0-6fd0a36d79db';
    app_slack UUID := 'c9a8e15e-4547-4d29-8b13-6bf4d1c6d0f4';
    -- entitlements
    ent_gsuite_admin UUID := '9da46f41-6854-41ac-96d9-0b0f91c2387e';
    ent_gsuite_user UUID := '7ef4b147-98d3-454b-bf32-64cf1aeb32c9';
    ent_aws_admin UUID := 'f362c831-13b4-424d-a5d3-d60162dbcb4f';
    ent_aws_view UUID := '965ad802-4bb1-4809-9c79-2d16451d92c5';
    ent_jira_admin UUID := 'a5d493c0-6cde-44e0-9e35-5bc3ed33a0e0';
    ent_jira_user UUID := 'c5d1a3a2-6b26-4c6a-8d48-8b0a455f4e6d';
    ent_slack_admin UUID := 'f8c9818f-15f7-4f96-8a83-3fdfd3026243';
    ent_slack_user UUID := '0e9f7d7b-8b6c-4465-9b30-c5d2d6aa2bde';
    -- access profiles
    ap_standard UUID := '2c8d13d8-3ca8-4df9-a650-0a7da5df9b98';
    ap_secops UUID := 'b1bcedd5-6f57-4ad5-98e1-4bfbc2515127';
    ap_compliance UUID := '80cd7016-f560-473b-a6fe-c7512d611cf9';
BEGIN
    SELECT id, customer_id INTO t, cust FROM tenants WHERE slug = 'demo' LIMIT 1;
    IF t IS NULL THEN
        RAISE NOTICE 'demo tenant not found; skipping IAM apps/devices';
        RETURN;
    END IF;

    -- Teams / orgs
    INSERT INTO public.organizations (id, customer_id, name, slug, realm_name, org_type, status)
    VALUES
        (org_sec, cust, 'Security Operations', 'demo-secops', 'demo', 'team', 'active'),
        (org_eng, cust, 'Product Engineering', 'demo-eng', 'demo', 'team', 'active')
    ON CONFLICT (id) DO UPDATE
    SET name = EXCLUDED.name,
        slug = EXCLUDED.slug,
        org_type = EXCLUDED.org_type,
        status = EXCLUDED.status,
        updated_at = now();

    UPDATE public.user_tenants
    SET organization_id = org_sec
    WHERE tenant_id = t AND user_id IN ('demo-admin','demo-analyst');
    UPDATE public.user_tenants
    SET organization_id = org_eng
    WHERE tenant_id = t AND user_id = 'demo-compliance';

    -- Apps (catalog for this tenant)
    INSERT INTO public.apps (id, tenant_id, name, display_name, description, app_type, icon_url, is_active, config)
    VALUES
        (app_google, t, 'google-workspace', 'Google Workspace', 'SSO + provisioning for Workspace', 'saml', 'https://logo.clearbit.com/google.com', true, '{"protocol":"saml","acs_url":"https://workspace.demo/acs","redirect_uris":["https://workspace.demo"]}'::jsonb),
        (app_aws, t, 'aws', 'AWS Production', 'SSO into AWS with role guardrails', 'oidc', 'https://logo.clearbit.com/aws.amazon.com', true, '{"protocol":"oidc","redirect_uris":["https://signin.aws.amazon.com/saml"]}'::jsonb),
        (app_jira, t, 'jira', 'Jira Cloud', 'Project management and ticketing', 'saml', 'https://logo.clearbit.com/atlassian.com', true, '{"protocol":"saml","redirect_uris":["https://demo.atlassian.net"]}'::jsonb),
        (app_slack, t, 'slack', 'Slack', 'Messaging for demo org', 'saml', 'https://logo.clearbit.com/slack.com', true, '{"protocol":"saml","redirect_uris":["https://demo.slack.com"]}'::jsonb)
    ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name, description = EXCLUDED.description, is_active = EXCLUDED.is_active, config = EXCLUDED.config, icon_url = EXCLUDED.icon_url;

    -- Entitlements / roles
    INSERT INTO public.entitlements (id, tenant_id, app_id, name, display_name, description, entitlement_type, is_privileged, requires_mfa, risk_level)
    VALUES
        (ent_gsuite_admin, t, app_google, 'workspace-admin', 'Workspace Admin', 'Full admin rights in Workspace', 'role', true, true, 'high'),
        (ent_gsuite_user, t, app_google, 'workspace-user', 'Workspace User', 'Standard Workspace access', 'role', false, false, 'low'),
        (ent_aws_admin, t, app_aws, 'aws-admin', 'AWS Admin', 'Admin role into AWS', 'role', true, true, 'high'),
        (ent_aws_view, t, app_aws, 'aws-readonly', 'AWS ReadOnly', 'Read-only AWS access', 'role', false, false, 'medium'),
        (ent_jira_admin, t, app_jira, 'jira-admin', 'Jira Admin', 'Jira site admin', 'role', true, true, 'medium'),
        (ent_jira_user, t, app_jira, 'jira-user', 'Jira User', 'Standard Jira access', 'role', false, false, 'low'),
        (ent_slack_admin, t, app_slack, 'slack-admin', 'Slack Admin', 'Slack workspace admin', 'role', true, true, 'medium'),
        (ent_slack_user, t, app_slack, 'slack-user', 'Slack User', 'Standard Slack access', 'role', false, false, 'low')
    ON CONFLICT (id) DO NOTHING;

    -- Access profiles (bundles)
    INSERT INTO public.access_profiles (id, tenant_id, name, display_name, description, is_default, is_system, is_birthright, scope)
    VALUES
        (ap_standard, t, 'standard-employee', 'Standard Employee', 'Baseline access for employees', true, true, true, 'all_users'),
        (ap_secops, t, 'secops-analyst', 'SecOps Analyst', 'Access for security analysts', false, false, false, 'team'),
        (ap_compliance, t, 'compliance-reviewer', 'Compliance Reviewer', 'Access for compliance/GRC users', false, false, false, 'team')
    ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, display_name = EXCLUDED.display_name, description = EXCLUDED.description, is_default = EXCLUDED.is_default, is_birthright = EXCLUDED.is_birthright, scope = EXCLUDED.scope;

    -- Access profile entitlements
    DELETE FROM public.access_profile_entitlements WHERE access_profile_id IN (ap_standard, ap_secops, ap_compliance);
    INSERT INTO public.access_profile_entitlements (access_profile_id, entitlement_id)
    VALUES
        (ap_standard, ent_gsuite_user),
        (ap_standard, ent_jira_user),
        (ap_standard, ent_slack_user),
        (ap_secops, ent_gsuite_user),
        (ap_secops, ent_aws_view),
        (ap_secops, ent_slack_user),
        (ap_secops, ent_jira_user),
        (ap_compliance, ent_gsuite_user),
        (ap_compliance, ent_jira_user),
        (ap_compliance, ent_slack_user)
    ON CONFLICT DO NOTHING;

    -- User entitlements (ensure idempotent)
    DELETE FROM public.user_entitlements
    WHERE tenant_id = t
      AND user_id IN ('demo-admin', 'demo-analyst', 'demo-compliance')
      AND entitlement_id IN (ent_gsuite_admin, ent_gsuite_user, ent_aws_admin, ent_aws_view, ent_jira_admin, ent_jira_user, ent_slack_admin, ent_slack_user);

    INSERT INTO public.user_entitlements (tenant_id, user_id, entitlement_id, granted_by)
    VALUES
        (t, 'demo-admin', ent_gsuite_admin, 'seed'),
        (t, 'demo-admin', ent_aws_admin, 'seed'),
        (t, 'demo-admin', ent_jira_admin, 'seed'),
        (t, 'demo-admin', ent_slack_admin, 'seed'),
        (t, 'demo-analyst', ent_gsuite_user, 'seed'),
        (t, 'demo-analyst', ent_aws_view, 'seed'),
        (t, 'demo-analyst', ent_slack_user, 'seed'),
        (t, 'demo-analyst', ent_jira_user, 'seed'),
        (t, 'demo-compliance', ent_gsuite_user, 'seed'),
        (t, 'demo-compliance', ent_jira_user, 'seed'),
        (t, 'demo-compliance', ent_slack_user, 'seed')
    ON CONFLICT DO NOTHING;

    -- Devices (assets table)
    DELETE FROM public.assets WHERE tenant_id = t AND asset_id IN ('demo-laptop-01','demo-laptop-02','demo-mobile-01');
    INSERT INTO public.assets (tenant_id, asset_id, asset_type, name, hostname, operating_system, os_version, ip_address, owner, user_id, department, compliance_status, metadata, last_seen_at)
    VALUES
        (t, 'demo-laptop-01', 'laptop', 'Admin MacBook', 'demo-mac-01', 'macOS', '14.3', '10.0.0.10', 'demo-admin@demo.sentinelgrid.ai', 'demo-admin', 'Security', 'compliant',
            '{"trust_status":"trusted","security_posture":{"score":92,"signals":{"disk_encrypted":true,"firewall_enabled":true,"os_patch_level":"current"}}}'::jsonb, now() - interval '5 minutes'),
        (t, 'demo-laptop-02', 'laptop', 'Analyst Laptop', 'demo-win-01', 'Windows', '11.0', '10.0.0.11', 'demo-analyst@demo.sentinelgrid.ai', 'demo-analyst', 'Security', 'compliant',
            '{"trust_status":"trusted","security_posture":{"score":88,"signals":{"disk_encrypted":true,"av_installed":true,"os_patch_level":"current"}}}'::jsonb, now() - interval '20 minutes'),
        (t, 'demo-mobile-01', 'mobile', 'Compliance iPad', 'demo-ipad-01', 'iOS', '17', '10.0.0.12', 'demo-compliance@demo.sentinelgrid.ai', 'demo-compliance', 'Compliance', 'compliant',
            '{"trust_status":"trusted","security_posture":{"score":90,"signals":{"disk_encrypted":true,"firewall_enabled":true}}}'::jsonb, now() - interval '1 hour');
END $$;

-- Tenant IAM policies
DO $$
DECLARE
    t UUID;
BEGIN
    SELECT id INTO t FROM tenants WHERE slug = 'demo' LIMIT 1;
    IF t IS NULL THEN
        RAISE NOTICE 'demo tenant not found; skipping policies';
        RETURN;
    END IF;

    INSERT INTO policies (id, tenant_id, name, display_name, description, policy_type, scope, scope_id, policy_data, is_active, priority, created_by, created_at, updated_at)
    VALUES (
        'f7ff8a5a-1034-4e0a-9d39-d0f79dea84ea',
        t,
        'demo-authz-tenant-baseline',
        'Demo Tenant Baseline',
        'Baseline tenant policy allowing admins and compliance roles.',
        'authorization',
        'tenant',
        NULL,
        '{"rules":[{"id":"allow-admins","conditions":[{"attribute":"role","operator":"in","value":["admin","compliance"]}],"actions":["allow"]}]}'::jsonb,
        TRUE,
        100,
        'seed',
        now(),
        now()
    )
    ON CONFLICT (id) DO NOTHING;
END $$;

-- Sample alerts for demo (populate UI)
DO $$
DECLARE
    t UUID;
    now_ts TIMESTAMPTZ := now();
BEGIN
    SELECT id INTO t FROM tenants WHERE slug = 'demo' LIMIT 1;
    IF t IS NULL THEN
        RAISE NOTICE 'demo tenant not found; skipping alerts';
        RETURN;
    END IF;

    INSERT INTO security_ops.alerts (id, tenant_id, source, external_id, title, description, raw_severity, status, detection_time, asset_id, user_identifier, raw_payload, nist_controls, mitre_tactics, mitre_techniques)
    VALUES
        ('8339b6b4-609d-4bb3-b635-057884f0585b', t, 'iam', 'ALRT-DEMO-001', 'Impossible travel detected for admin', 'Login from two distant regions within 5 minutes.', 'high', 'open', now_ts - interval '30 minutes', 'aws-demo', 'demo-admin', '{"rule":"ID-IMPOSSIBLE-TRAVEL"}', '["DE.CM"]'::jsonb, '["TA0001"]'::jsonb, '["T1078"]'::jsonb),
        ('371ff3d6-ac19-4dad-91a0-cbf4de71bd01', t, 'cloudtrail', 'ALRT-DEMO-002', 'Root account used in production', 'Root credentials used to access prod account.', 'critical', 'open', now_ts - interval '2 hours', 'aws-demo', NULL, '{"rule":"CLD-ROOT-USE"}', '["PR.AC"]'::jsonb, '["TA0001"]'::jsonb, '["T1078"]'::jsonb),
        ('5a643948-d0a6-4b1c-b2cc-1e1773d1458a', t, 'siem', 'ALRT-DEMO-003', 'Outbound connection to malicious domain', 'Egress to known malicious domain detected.', 'high', 'open', now_ts - interval '6 hours', 'device-demo-01', NULL, '{"rule":"NW-OUTBOUND-MALICIOUS"}', '["DE.CM"]'::jsonb, '["TA0011"]'::jsonb, '["T1071"]'::jsonb)
    ON CONFLICT (id) DO NOTHING;
END $$;

-- Defend sample data (moved from V007)
DO $$
DECLARE
    t UUID;
    now_ts TIMESTAMPTZ := now();
    scan_cloud UUID := '11111111-1111-1111-1111-111111111111';
    scan_trivy UUID := '22222222-2222-2222-2222-222222222222';
    scan_git UUID := '33333333-3333-3333-3333-333333333333';
    scan_zap UUID := '44444444-4444-4444-4444-444444444444';
    fg_cloud UUID := 'aaaa1111-0000-0000-0000-000000000001';
    fg_trivy UUID := 'bbbb2222-0000-0000-0000-000000000002';
    fg_git UUID := 'cccc3333-0000-0000-0000-000000000003';
    fg_zap UUID := 'dddd4444-0000-0000-0000-000000000004';
BEGIN
    SELECT id INTO t FROM tenants WHERE slug = 'demo' LIMIT 1;
    IF t IS NULL THEN
        RAISE NOTICE 'demo tenant not found; skipping defend seeds';
        RETURN;
    END IF;

    -- Clear existing scans for idempotency (orchestration schema + public mirror)
    DELETE FROM orchestration.scans WHERE tenant_id = t;
    DELETE FROM scans WHERE tenant_id = t;

    INSERT INTO orchestration.scans (id, tenant_id, scanner_id, target_ref, status, created_at, updated_at, started_at, finished_at, summary)
    VALUES
        (scan_cloud, t, 'cloud', 'aws-demo', 'completed', now_ts, now_ts, now_ts - INTERVAL '30 minutes', now_ts - INTERVAL '25 minutes', '{"findings":2,"severity":"high"}'),
        (scan_trivy, t, 'trivy', 'device-demo-01', 'completed', now_ts, now_ts, now_ts - INTERVAL '75 minutes', now_ts - INTERVAL '70 minutes', '{"findings":5,"severity":"critical","type":"vulnerability","target_kind":"device"}'),
        (scan_git, t, 'git', 'github/demo/repo', 'completed', now_ts, now_ts, now_ts - INTERVAL '2 hours', now_ts - INTERVAL '110 minutes', '{"findings":0,"severity":"low"}'),
        (scan_zap, t, 'zap', 'https://demo.app/login', 'completed', now_ts, now_ts, now_ts - INTERVAL '3 hours', now_ts - INTERVAL '175 minutes', '{"findings":3,"severity":"medium","type":"vulnerability","target_kind":"app"}')
    ON CONFLICT (id) DO NOTHING;

    -- Mirror scans into public.scans to satisfy fix_group FK
    INSERT INTO scans (id, tenant_id, scanner_id, target_ref, status, created_at, updated_at, started_at, finished_at, summary)
    VALUES
        (scan_cloud, t, 'cloud', 'aws-demo', 'completed', now_ts, now_ts, now_ts - INTERVAL '30 minutes', now_ts - INTERVAL '25 minutes', '{"findings":2,"severity":"high"}'),
        (scan_trivy, t, 'trivy', 'device-demo-01', 'completed', now_ts, now_ts, now_ts - INTERVAL '75 minutes', now_ts - INTERVAL '70 minutes', '{"findings":5,"severity":"critical","type":"vulnerability","target_kind":"device"}'),
        (scan_git, t, 'git', 'github/demo/repo', 'completed', now_ts, now_ts, now_ts - INTERVAL '2 hours', now_ts - INTERVAL '110 minutes', '{"findings":0,"severity":"low"}'),
        (scan_zap, t, 'zap', 'https://demo.app/login', 'completed', now_ts, now_ts, now_ts - INTERVAL '3 hours', now_ts - INTERVAL '175 minutes', '{"findings":3,"severity":"medium","type":"vulnerability","target_kind":"app"}')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO fix_groups (id, tenant_id, scan_id, type, description, fixed_in_target, priority, sla_due, status, created_at, updated_at, ai_guidance, ticket_id, ticket_status)
    VALUES
        (fg_cloud, t, scan_cloud, 'patch_group', 'Apply cloud patches for aws-demo', NULL, 'P1', now_ts + INTERVAL '7 days', 'open', now_ts, now_ts,
            '{"summary":"Apply cloud patches for aws-demo","steps":["Review failing controls","Apply vendor patches","Re-run the scan"],"validation":["Re-run the originating scan"]}', NULL, NULL),
        (fg_trivy, t, scan_trivy, 'dependency_upgrade', 'Rebuild base image for device-demo-01', 'base:2024.01', 'P0', now_ts + INTERVAL '72 hours', 'open', now_ts, now_ts,
            '{"summary":"Upgrade dependencies/base image for device-demo-01","steps":["Identify vulnerable packages","Rebuild image with patched base","Re-run scan and smoke tests"],"validation":["Re-run the originating scan"]}', 'TKT-DEMO-1', 'open'),
        (fg_git, t, scan_git, 'dependency_upgrade', 'Review repo findings for github/demo/repo', NULL, 'P2', now_ts + INTERVAL '30 days', 'open', now_ts, now_ts,
            '{"summary":"Address repo findings","steps":["Fix SAST/secret issues","Run CI security scans","Re-run scan"],"validation":["Re-run the originating scan"]}', NULL, NULL),
        (fg_zap, t, scan_zap, 'dependency_upgrade', 'Fix web findings for demo app login', NULL, 'P2', now_ts + INTERVAL '30 days', 'open', now_ts, now_ts,
            '{"summary":"Fix web vulns for demo app login","steps":["Review ZAP findings","Patch/mitigate vulnerable routes","Re-run DAST"],"validation":["Re-run the originating scan"]}', NULL, NULL)
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO fix_group_assets (fix_group_id, tenant_id, asset_ref, asset_type)
    VALUES
        (fg_cloud, t, 'aws-demo', 'cloud'),
        (fg_trivy, t, 'device-demo-01', 'trivy'),
        (fg_git, t, 'github/demo/repo', 'git'),
        (fg_zap, t, 'https://demo.app/login', 'zap')
    ON CONFLICT (fix_group_id, asset_ref) DO NOTHING;

    INSERT INTO fix_group_cves (fix_group_id, tenant_id, cve_id)
    VALUES
        (fg_cloud, t, 'CVE-2024-1234'),
        (fg_trivy, t, 'CVE-2024-1234'),
        (fg_trivy, t, 'CVE-2023-9999'),
        (fg_zap, t, 'CVE-2022-5555')
    ON CONFLICT (fix_group_id, cve_id) DO NOTHING;
END $$;

-- Compliance reports (moved from V122/V123)
DO $$
DECLARE
    t UUID;
BEGIN
    SELECT id INTO t FROM tenants WHERE slug = 'demo' LIMIT 1;
    IF t IS NULL THEN
        RAISE NOTICE 'demo tenant not found; skipping compliance reports';
        RETURN;
    END IF;

    INSERT INTO reporting.reports (id, tenant_id, template_id, name, format, status, generated_at, created_at, updated_at, sections, metadata, download_url)
    VALUES
        ('7c6fe55d-25fd-47ac-ae09-73b28ef159f6', t, NULL, 'SOC 2 Coverage Snapshot', 'PDF', 'COMPLETED', now(), now(), now(),
         '["Executive Summary","Coverage","Gaps","Recommendations"]'::jsonb,
         jsonb_build_object('report_type','soc2_coverage','period_start','2024-11-01','period_end','2024-11-30','coverage_percent',82,'controls_implemented',38,'controls_total',46),
         'https://localhost:8010/reports/demo/soc2-coverage.pdf')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO reporting.reports (id, tenant_id, template_id, name, format, status, generated_at, created_at, updated_at, sections, metadata, download_url)
    VALUES
        ('38b7e6cf-b5f0-4d17-bd01-200c0549ba40', t, NULL, 'Cloud Posture Report', 'PDF', 'COMPLETED', now(), now(), now(),
         '["Executive Summary","Findings","Top Risks","Remediation Plan"]'::jsonb,
         jsonb_build_object('report_type','cloud_posture','high_findings',5,'medium_findings',12,'low_findings',18,'externally_exposed',3),
         'https://localhost:8010/reports/demo/cloud-posture.pdf')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO reporting.reports (id, tenant_id, template_id, name, format, status, generated_at, created_at, updated_at, sections, metadata, download_url)
    VALUES
        ('cca3e097-7601-4afe-81f7-6d389aa0bbcf', t, NULL, 'NIST CSF Coverage', 'PDF', 'COMPLETED', now(), now(), now(),
         '["Identify","Protect","Detect","Respond","Recover"]'::jsonb,
         jsonb_build_object('report_type','nist_csf','identify',0.78,'protect',0.74,'detect',0.69,'respond',0.72,'recover',0.76),
         'https://localhost:8010/reports/demo/nist-csf.pdf')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO reporting.reports (id, tenant_id, template_id, name, format, status, generated_at, created_at, updated_at, sections, metadata, download_url)
    VALUES
        ('af5da4a1-7c17-4aa0-bc58-a6c8720e3fa0', t, NULL, 'IAM & MFA Hygiene', 'PDF', 'COMPLETED', now(), now(), now(),
         '["Executive Summary","Coverage","Gaps","Recommendations"]'::jsonb,
         jsonb_build_object('report_type','iam_mfa_hygiene','mfa_coverage',0.86,'inactive_accounts',3,'excess_privileged_accounts',1),
         'https://localhost:8014/reports/demo/iam-mfa.pdf')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO reporting.reports (id, tenant_id, template_id, name, format, status, generated_at, created_at, updated_at, sections, metadata, download_url)
    VALUES
        ('ab85a90d-6fc8-4073-9a7e-50944567eebc', t, NULL, 'Log Coverage', 'PDF', 'COMPLETED', now(), now(), now(),
         '["Executive Summary","Sources","Gaps","Actions"]'::jsonb,
         jsonb_build_object('report_type','log_coverage','sources_reporting',18,'sources_missing',2,'critical_gaps',1),
         'https://localhost:8014/reports/demo/log-coverage.pdf')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO reporting.reports (id, tenant_id, template_id, name, format, status, generated_at, created_at, updated_at, sections, metadata, download_url)
    VALUES
        ('6fd2ed41-dae9-4b79-a5cf-1c6b7fe3239e', t, NULL, 'Incident Response Readiness', 'PDF', 'COMPLETED', now(), now(), now(),
         '["Executive Summary","Playbooks","MTTD/MTTR","Recommendations"]'::jsonb,
         jsonb_build_object('report_type','incident_response','mttd_hours',1.8,'mttr_hours',5.4,'playbooks_ready',12),
         'https://localhost:8014/reports/demo/ir-readiness.pdf')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO reporting.reports (id, tenant_id, template_id, name, format, status, generated_at, created_at, updated_at, sections, metadata, download_url)
    VALUES
        ('ee43098c-605d-444a-bdb9-b6e3070dd09f', t, NULL, 'Security One-Pager', 'PDF', 'COMPLETED', now(), now(), now(),
         '["Snapshot","Top Risks","Actions"]'::jsonb,
         jsonb_build_object('report_type','security_onepager','risk_score',72,'top_alerts',5,'open_actions',8),
         'https://localhost:8014/reports/demo/security-onepager.pdf')
    ON CONFLICT (id) DO NOTHING;
END $$;

COMMIT;
