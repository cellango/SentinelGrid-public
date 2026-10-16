-- Enrich demo scans for SAST, secrets, IaC, git, and cloud with richer summaries.

DO $$
DECLARE
    demo_tenant UUID := 'ff1c2b60-1fd6-46d1-8458-b0484f5d58f8';
    demo2_tenant UUID := 'b210c499-ea35-4e15-8b93-cd2446361d27';
BEGIN
    -- Cloud posture
    UPDATE scans
    SET summary = jsonb_build_object(
        'findings', 2,
        'severity', 'high',
        'type', 'cloud',
        'soc2_criteria', jsonb_build_array('CC7.1','CC8.1','CC9.1'),
        'externally_exposed', false,
        'nist_controls', jsonb_build_array('RA-5','CM-6'),
        'mitre_techniques', jsonb_build_array('T1580'),
        'failing_controls', jsonb_build_array(
            jsonb_build_object('id','S3-001','description','Public bucket access allowed','remediation','Enable block public access'),
            jsonb_build_object('id','IAM-002','description','IAM key older than 90 days','remediation','Rotate access keys')
        ),
        'remediation', jsonb_build_object(
            'summary','Tighten cloud posture controls.',
            'steps', jsonb_build_array(
                'Enable GuardDuty/CloudTrail for all regions',
                'Restrict public buckets and rotate IAM keys',
                'Re-run cloud posture scan'
            ),
            'validation', jsonb_build_array('Cloud posture scan returns zero high-risk findings')
        )
    )
    WHERE tenant_id IN (demo_tenant, demo2_tenant) AND scanner_id IN ('cloud','prowler');

    -- DAST/web
    UPDATE scans
    SET summary = jsonb_build_object(
        'findings', 3,
        'severity', 'high',
        'type', 'dast',
        'target_url', 'https://demo.app/login',
        'evidence', 'Reflected parameter accepted script payload',
        'target_kind', 'app',
        'soc2_criteria', jsonb_build_array('CC7.1','CC9.1'),
        'externally_exposed', true,
        'cves', jsonb_build_array(
            jsonb_build_object('id','CVE-2022-5555','cvss',7.5,'description','Input validation flaw on login form','fix','Apply input validation patch')
        ),
        'nist_controls', jsonb_build_array('RA-5','SI-10'),
        'mitre_techniques', jsonb_build_array('T1190','T1059.007'),
        'remediation', jsonb_build_object(
            'summary','Patch the login form and tighten input validation.',
            'steps', jsonb_build_array(
                'Enable server-side validation for login parameters',
                'Deploy WAF rule to block injection attempts',
                'Re-test with DAST to confirm issue is closed'
            ),
            'validation', jsonb_build_array('Re-run DAST scan','Verify no high findings remain')
        )
    )
    WHERE tenant_id IN (demo_tenant, demo2_tenant) AND scanner_id = 'zap';

    -- SAST (semgrep)
    UPDATE scans
    SET summary = jsonb_build_object(
        'findings', 4,
        'severity', 'high',
        'type', 'sast',
        'file_path', 'src/auth/login.py',
        'line', 128,
        'rule_id', 'sg.auth.injection',
        'cwe', 'CWE-89',
        'nist_controls', jsonb_build_array('RA-5','CM-7'),
        'mitre_techniques', jsonb_build_array('T1036'),
        'remediation', jsonb_build_object(
            'summary','Sanitize SQL inputs in login flow.',
            'steps', jsonb_build_array(
                'Use parameterized queries for DB access',
                'Add input validation for username/password fields',
                'Re-run SAST on the repo'
            ),
            'validation', jsonb_build_array('SAST scan reports zero high findings for CWE-89')
        )
    )
    WHERE tenant_id IN (demo_tenant, demo2_tenant) AND scanner_id = 'semgrep';

    -- Secrets (gitleaks)
    UPDATE scans
    SET summary = jsonb_build_object(
        'findings', 1,
        'severity', 'high',
        'type', 'secrets',
        'file_path', 'config/.env',
        'line', 12,
        'secret_type', 'AWS Access Key',
        'secret_sample', 'AKIA****',
        'nist_controls', jsonb_build_array('CM-8'),
        'mitre_techniques', jsonb_build_array('T1552'),
        'remediation', jsonb_build_object(
            'summary','Rotate exposed AWS key and purge from repo history.',
            'steps', jsonb_build_array(
                'Invalidate and rotate the AWS access key',
                'Purge the secret from git history',
                'Add pre-commit secret scanning'
            ),
            'validation', jsonb_build_array('Secret scan reports zero findings','New key validated in CI')
        )
    )
    WHERE tenant_id IN (demo_tenant, demo2_tenant) AND scanner_id = 'gitleaks';

    -- IaC (checkov)
    UPDATE scans
    SET summary = jsonb_build_object(
        'findings', 3,
        'severity', 'medium',
        'type', 'iac',
        'resource', 'aws_s3_bucket.demo',
        'control_id', 'CKV_AWS_20',
        'desired_state', 'block public access, enable encryption',
        'nist_controls', jsonb_build_array('CM-6'),
        'mitre_techniques', jsonb_build_array('T1552'),
        'remediation', jsonb_build_object(
            'summary','Harden IaC for S3 bucket.',
            'steps', jsonb_build_array(
                'Set block_public_acls and block_public_policy to true',
                'Enable default encryption (SSE)',
                'Re-run IaC scan in CI'
            ),
            'validation', jsonb_build_array('IaC scan returns zero medium/high findings')
        )
    )
    WHERE tenant_id IN (demo_tenant, demo2_tenant) AND scanner_id = 'checkov';

    -- Git hygiene
    UPDATE scans
    SET summary = jsonb_build_object(
        'findings', 0,
        'severity', 'low',
        'type', 'git',
        'repo', 'github/demo/repo',
        'branch', 'main',
        'last_commit', 'abcdef123456',
        'soc2_criteria', jsonb_build_array('CC8.1','CC4.1'),
        'remediation', jsonb_build_object('summary','No action required','steps', jsonb_build_array(),'validation', jsonb_build_array())
    )
    WHERE tenant_id IN (demo_tenant, demo2_tenant) AND scanner_id = 'git';
END $$;
