-- Enrich demo scan summaries with CVEs, remediation, and external exposure flags.

DO $$
DECLARE
    demo_tenant UUID := 'ff1c2b60-1fd6-46d1-8458-b0484f5d58f8';
    demo2_tenant UUID := 'b210c499-ea35-4e15-8b93-cd2446361d27';
BEGIN
    -- Trivy/container vuln
    UPDATE scans
    SET summary = jsonb_build_object(
        'findings', 5,
        'severity', 'critical',
        'type', 'vuln',
        'target_kind', 'device',
        'cves', jsonb_build_array(
            jsonb_build_object('id','CVE-2024-1234','cvss',9.1,'description','OpenSSL critical vuln','fix','Upgrade to OpenSSL 3.0.14'),
            jsonb_build_object('id','CVE-2023-9999','cvss',8.2,'description','Kernel privilege escalation','fix','Apply kernel patch >= 5.15.120')
        ),
        'remediation', jsonb_build_object(
            'summary','Rebuild the base image with patched OpenSSL and kernel updates.',
            'steps', jsonb_build_array(
                'Update base image to latest LTS with patched OpenSSL',
                'Rebuild and redeploy containers consuming this image',
                'Re-run container vulnerability scan to verify closure'
            ),
            'validation', jsonb_build_array(
                'Re-run the originating scan',
                'Check CI pipeline for zero critical vulns'
            )
        )
    )
    WHERE tenant_id IN (demo_tenant, demo2_tenant) AND scanner_id = 'trivy';

    -- DAST/web
    UPDATE scans
    SET summary = jsonb_build_object(
        'findings', 3,
        'severity', 'high',
        'type', 'dast',
        'target_kind', 'app',
        'externally_exposed', true,
        'cves', jsonb_build_array(
            jsonb_build_object('id','CVE-2022-5555','cvss',7.5,'description','Input validation flaw on login form','fix','Apply input validation patch')
        ),
        'remediation', jsonb_build_object(
            'summary','Patch the login form and tighten input validation.',
            'steps', jsonb_build_array(
                'Enable server-side validation for login parameters',
                'Deploy WAF rule to block injection attempts',
                'Re-test with DAST to confirm issue is closed'
            ),
            'validation', jsonb_build_array(
                'Re-run DAST scan',
                'Verify no high findings remain'
            )
        )
    )
    WHERE tenant_id IN (demo_tenant, demo2_tenant) AND scanner_id = 'zap';

    -- Cloud posture
    UPDATE scans
    SET summary = jsonb_build_object(
        'findings', 2,
        'severity', 'high',
        'type', 'cloud',
        'externally_exposed', false,
        'remediation', jsonb_build_object(
            'summary','Tighten cloud posture controls.',
            'steps', jsonb_build_array(
                'Enable GuardDuty/CloudTrail for all regions',
                'Restrict public buckets and rotate IAM keys',
                'Re-run cloud posture scan'
            ),
            'validation', jsonb_build_array(
                'Cloud posture scan returns zero high-risk findings'
            )
        )
    )
    WHERE tenant_id IN (demo_tenant, demo2_tenant) AND scanner_id IN ('cloud','prowler');
END $$;
