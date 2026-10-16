-- Backfill NIST controls and MITRE techniques into demo scan summaries for richer UI.

DO $$
DECLARE
    demo_tenant UUID := 'ff1c2b60-1fd6-46d1-8458-b0484f5d58f8';
    demo2_tenant UUID := 'b210c499-ea35-4e15-8b93-cd2446361d27';
BEGIN
    -- Cloud posture (cloud/prowler)
    UPDATE scans
    SET summary = summary
        || jsonb_build_object(
            'nist_controls', jsonb_build_array('RA-5','CM-6'),
            'mitre_techniques', jsonb_build_array('T1580')
        )
    WHERE tenant_id IN (demo_tenant, demo2_tenant) AND scanner_id IN ('cloud','prowler');

    -- Trivy/container vuln
    UPDATE scans
    SET summary = summary
        || jsonb_build_object(
            'nist_controls', jsonb_build_array('RA-5','SI-2'),
            'mitre_techniques', jsonb_build_array('T1190','T1059.004')
        )
    WHERE tenant_id IN (demo_tenant, demo2_tenant) AND scanner_id = 'trivy';

    -- DAST/web
    UPDATE scans
    SET summary = summary
        || jsonb_build_object(
            'nist_controls', jsonb_build_array('RA-5','SI-10'),
            'mitre_techniques', jsonb_build_array('T1190','T1059.007')
        )
    WHERE tenant_id IN (demo_tenant, demo2_tenant) AND scanner_id = 'zap';
END $$;
