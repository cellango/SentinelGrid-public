-- Seed a host/VM scan sample for demo tenants with NIST/MITRE and remediation.

DO $$
DECLARE
    demo_tenant UUID := 'ff1c2b60-1fd6-46d1-8458-b0484f5d58f8';
    demo2_tenant UUID := 'b210c499-ea35-4e15-8b93-cd2446361d27';
    now_ts TIMESTAMPTZ := now();
BEGIN
    INSERT INTO scans (id, tenant_id, scanner_id, scan_type, target_ref, status, created_at, updated_at, started_at, finished_at, summary)
    VALUES
        (gen_random_uuid(), demo_tenant, 'host', 'host', 'vm-demo-01', 'completed', now_ts, now_ts, now_ts - interval '4 hours', now_ts - interval '3 hours 55 minutes',
            '{
                "findings":4,
                "severity":"high",
                "type":"host",
                "target_kind":"vm",
                "externally_exposed":false,
                "cves":[
                    {"id":"CVE-2024-2001","cvss":8.0,"description":"Kernel network stack vuln","fix":"Update kernel to 5.15.120"},
                    {"id":"CVE-2023-7777","cvss":7.2,"description":"OpenSSH privilege issue","fix":"Upgrade to OpenSSH 9.8p1"}
                ],
                "nist_controls":["RA-5","SI-2"],
                "mitre_techniques":["T1068","T1047"],
                "remediation":{
                    "summary":"Patch kernel and OpenSSH, then re-run host scan.",
                    "steps":[
                        "Apply latest distro kernel and reboot during a maintenance window",
                        "Upgrade OpenSSH to 9.8p1 and rotate keys if needed",
                        "Re-run host vulnerability scan to confirm closure"
                    ],
                    "validation":[
                        "Host scan reports zero high findings",
                        "Confirm OpenSSH version matches patched release"
                    ]
                }
            }'::jsonb)
    ON CONFLICT DO NOTHING;

    INSERT INTO scans (id, tenant_id, scanner_id, scan_type, target_ref, status, created_at, updated_at, started_at, finished_at, summary)
    VALUES
        (gen_random_uuid(), demo2_tenant, 'host', 'host', 'vm-demo-02', 'completed', now_ts, now_ts, now_ts - interval '3 hours 40 minutes', now_ts - interval '3 hours 35 minutes',
            '{
                "findings":3,
                "severity":"medium",
                "type":"host",
                "target_kind":"vm",
                "externally_exposed":false,
                "cves":[
                    {"id":"CVE-2023-2002","cvss":6.5,"description":"glibc buffer issue","fix":"Update glibc to latest stable"}
                ],
                "nist_controls":["RA-5","CM-6"],
                "mitre_techniques":["T1068"],
                "remediation":{
                    "summary":"Apply latest system updates and re-run scan.",
                    "steps":[
                        "Update glibc via package manager",
                        "Restart impacted services",
                        "Re-run host vulnerability scan to verify"
                    ],
                    "validation":[
                        "Host scan reports zero medium/high findings"
                    ]
                }
            }'::jsonb)
    ON CONFLICT DO NOTHING;
END $$;
