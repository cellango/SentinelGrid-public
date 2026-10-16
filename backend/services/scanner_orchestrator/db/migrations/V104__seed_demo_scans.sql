-- Seed demo scans + FixGroups for demo tenant to support UI/Selenium tests.
-- Idempotent via ON CONFLICT DO NOTHING; uses stable UUIDs.

DO $$
DECLARE
    demo_tenant UUID := 'ff1c2b60-1fd6-46d1-8458-b0484f5d58f8';
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
    -- Scans
    INSERT INTO scans (id, tenant_id, scanner_id, target_ref, status, created_at, updated_at, started_at, finished_at, summary)
    VALUES
        (scan_cloud, demo_tenant, 'cloud', 'aws-demo', 'completed', now_ts, now_ts, now_ts - INTERVAL '30 minutes', now_ts - INTERVAL '25 minutes', '{"findings":2,"severity":"high"}'),
        (scan_trivy, demo_tenant, 'trivy', 'device-demo-01', 'completed', now_ts, now_ts, now_ts - INTERVAL '75 minutes', now_ts - INTERVAL '70 minutes', '{"findings":5,"severity":"critical","type":"vulnerability","target_kind":"device"}'),
        (scan_git, demo_tenant, 'git', 'github/demo/repo', 'completed', now_ts, now_ts, now_ts - INTERVAL '2 hours', now_ts - INTERVAL '110 minutes', '{"findings":0,"severity":"low"}'),
        (scan_zap, demo_tenant, 'zap', 'https://demo.app/login', 'completed', now_ts, now_ts, now_ts - INTERVAL '3 hours', now_ts - INTERVAL '175 minutes', '{"findings":3,"severity":"medium","type":"vulnerability","target_kind":"app"}')
    ON CONFLICT (id) DO NOTHING;

    -- FixGroups with guidance, assets, CVEs, and a seeded ticket on the trivy scan
    INSERT INTO fix_groups (id, tenant_id, scan_id, type, description, fixed_in_target, priority, sla_due, status, created_at, updated_at, ai_guidance, ticket_id, ticket_status)
    VALUES
        (fg_cloud, demo_tenant, scan_cloud, 'patch_group', 'Apply cloud patches for aws-demo', NULL, 'P1', now_ts + INTERVAL '7 days', 'open', now_ts, now_ts,
            '{"summary":"Apply cloud patches for aws-demo","steps":["Review failing controls","Apply vendor patches","Re-run the scan"],"validation":["Re-run the originating scan"]}', NULL, NULL),
        (fg_trivy, demo_tenant, scan_trivy, 'dependency_upgrade', 'Rebuild base image for device-demo-01', 'base:2024.01', 'P0', now_ts + INTERVAL '72 hours', 'open', now_ts, now_ts,
            '{"summary":"Upgrade dependencies/base image for device-demo-01","steps":["Identify vulnerable packages","Rebuild image with patched base","Re-run scan and smoke tests"],"validation":["Re-run the originating scan"]}', 'TKT-DEMO-1', 'open'),
        (fg_git, demo_tenant, scan_git, 'dependency_upgrade', 'Review repo findings for github/demo/repo', NULL, 'P2', now_ts + INTERVAL '30 days', 'open', now_ts, now_ts,
            '{"summary":"Address repo findings","steps":["Fix SAST/secret issues","Run CI security scans","Re-run scan"],"validation":["Re-run the originating scan"]}', NULL, NULL),
        (fg_zap, demo_tenant, scan_zap, 'dependency_upgrade', 'Fix web findings for demo app login', NULL, 'P2', now_ts + INTERVAL '30 days', 'open', now_ts, now_ts,
            '{"summary":"Fix web vulns for demo app login","steps":["Review ZAP findings","Patch/mitigate vulnerable routes","Re-run DAST"],"validation":["Re-run the originating scan"]}', NULL, NULL)
    ON CONFLICT (id) DO NOTHING;

    -- Asset links
    INSERT INTO fix_group_assets (fix_group_id, tenant_id, asset_ref, asset_type)
    VALUES
        (fg_cloud, demo_tenant, 'aws-demo', 'cloud'),
        (fg_trivy, demo_tenant, 'device-demo-01', 'trivy'),
        (fg_git, demo_tenant, 'github/demo/repo', 'git'),
        (fg_zap, demo_tenant, 'https://demo.app/login', 'zap')
    ON CONFLICT (fix_group_id, asset_ref) DO NOTHING;

    -- CVE links
    INSERT INTO fix_group_cves (fix_group_id, tenant_id, cve_id)
    VALUES
        (fg_cloud, demo_tenant, 'CVE-2024-1234'),
        (fg_trivy, demo_tenant, 'CVE-2024-1234'),
        (fg_trivy, demo_tenant, 'CVE-2023-9999'),
        (fg_zap, demo_tenant, 'CVE-2022-5555')
    ON CONFLICT (fix_group_id, cve_id) DO NOTHING;
END;
$$;
