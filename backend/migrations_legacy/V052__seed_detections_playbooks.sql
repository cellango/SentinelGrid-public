-- Seed built-in playbooks (30) and detection rules (100) into system and demo tenants.
-- System tenant: 00000000-0000-0000-0000-000000000000
-- Demo tenant:    c6d82f67-36f1-4c7e-af66-d1333e45cde7

DO $$
DECLARE
    sys  UUID := '00000000-0000-0000-0000-000000000000';
    demo UUID := 'c6d82f67-36f1-4c7e-af66-d1333e45cde7';
BEGIN
    -- Playbooks seed (30)
    WITH pb(key,name,description,target_type,category_filter,severity_filter,workflow_ref,requires_approval,tags,nist_controls,mitre_tactics,mitre_techniques) AS (
        VALUES
        ('ACCOUNT-COMPROMISE','Account Compromise / Suspicious Login','Respond to suspected account takeover','alert','["identity"]','{"min":"medium"}','account-compromise-workflow',true,ARRAY['identity'],ARRAY['PR.AC','DE.CM'],ARRAY['TA0001'],ARRAY['T1078']),
        ('PASSWORD-SPRAY','Password Spray Response','Contain password spray attempts','alert','["identity"]','{"min":"medium"}','password-spray-workflow',false,ARRAY['identity'],ARRAY['PR.AC','DE.CM'],ARRAY['TA0006'],ARRAY['T1110.003']),
        ('MFA-BYPASS','MFA Bypass / Disabled','Handle MFA disablement/bypass','alert','["identity"]','{"min":"high"}','mfa-bypass-workflow',true,ARRAY['identity'],ARRAY['PR.AC','DE.CM'],ARRAY['TA0006'],ARRAY['T1556']),
        ('PRIV-GROUP-CHANGE','Privileged Group Change','Review privileged group changes','alert','["identity"]','{"min":"high"}','priv-group-change-workflow',true,ARRAY['identity'],ARRAY['PR.AC','DE.CM'],ARRAY['TA0003'],ARRAY['T1098']),
        ('PHISH-USER','Phishing – User Reported','Handle user-reported phishing','alert','["phishing"]','{"min":"medium"}','phish-user-reported-workflow',true,ARRAY['phishing'],ARRAY['DE.CM','RS.MI'],ARRAY['TA0001'],ARRAY['T1566']),
        ('PHISH-GATEWAY','Phishing – Gateway Alert','Respond to SEG phishing detections','alert','["phishing"]','{"min":"high"}','phish-gateway-workflow',false,ARRAY['phishing'],ARRAY['DE.CM','RS.MI'],ARRAY['TA0001'],ARRAY['T1566']),
        ('EXEC-NOTIFY','Executive Notify','Summarize/notify exec stakeholders','alert','["phishing","identity","cloud","endpoint"]','{"min":"medium"}','exec-notify-workflow',false,ARRAY['exec'],ARRAY['RS.CO'],ARRAY[]::text[],ARRAY[]::text[]),
        ('ENDPOINT-ISOLATE','Endpoint Isolation','Isolate/contain endpoint','alert','["endpoint"]','{"min":"medium"}','endpoint-isolate-workflow',true,ARRAY['endpoint'],ARRAY['DE.CM','RS.MI'],ARRAY['TA0008'],ARRAY['T1105','T1059']),
        ('MALWARE-CONTAIN','Malware Containment','Contain malware on host','alert','["endpoint","malware"]','{"min":"high"}','malware-contain-workflow',true,ARRAY['endpoint','malware'],ARRAY['DE.CM','RS.MI'],ARRAY['TA0002'],ARRAY['T1059','T1204']),
        ('RANSOMWARE-IR','Ransomware IR','Emergency containment and recovery','alert','["endpoint","ransomware"]','{"min":"high"}','ransomware-ir-workflow',false,ARRAY['endpoint','ransomware'],ARRAY['DE.CM','RS.MI'],ARRAY['TA0040'],ARRAY['T1486']),
        ('WAF-ATTACK','Web App Attack Response','Handle web attack/WAF alerts','alert','["web","network"]','{"min":"medium"}','waf-attack-workflow',false,ARRAY['network','web'],ARRAY['DE.CM','RS.MI'],ARRAY['TA0001'],ARRAY['T1190']),
        ('C2/BEACON','C2 / Beacon Response','Investigate C2/beaconing','alert','["network"]','{"min":"high"}','c2-beacon-workflow',false,ARRAY['network'],ARRAY['DE.CM','RS.MI'],ARRAY['TA0011'],ARRAY['T1071']),
        ('EGRESS-ANOMALY','Egress Anomaly Response','Investigate unusual egress','alert','["network","cloud"]','{"min":"high"}','egress-anomaly-workflow',false,ARRAY['network','cloud'],ARRAY['DE.CM','RS.MI'],ARRAY['TA0010'],ARRAY['T1041']),
        ('CLOUD-PUBLIC-STORAGE','Cloud Public Storage Remediation','Remediate public storage','finding','["cloud","posture"]','{"min":"high"}','public-storage-workflow',true,ARRAY['cloud','posture'],ARRAY['PR.DS','DE.CM'],ARRAY[]::text[],ARRAY[]::text[]),
        ('SG-OPEN-CRITICAL','Open Security Group Remediation','Close open SG on critical ports','finding','["cloud","network"]','{"min":"high"}','sg-open-critical-workflow',true,ARRAY['cloud','network'],ARRAY['PR.AC','PR.DS'],ARRAY[]::text[],ARRAY[]::text[]),
        ('ROOT-USE','Root Use Response','Handle root/break-glass use','alert','["cloud","identity"]','{"min":"high"}','root-use-workflow',true,ARRAY['cloud','identity'],ARRAY['PR.AC','DE.CM'],ARRAY['TA0001'],ARRAY['T1078']),
        ('K8S-PRIV-POD','K8s Privileged Pod Response','Handle privileged/host pods','finding','["cloud","k8s"]','{"min":"high"}','k8s-priv-pod-workflow',true,ARRAY['cloud','k8s'],ARRAY['PR.IP','DE.CM'],ARRAY[]::text[],ARRAY[]::text[]),
        ('KMS-KEY-DISABLED','KMS Key Disabled/Deletion','Investigate KMS key disable/delete','alert','["cloud"]','{"min":"high"}','kms-key-disabled-workflow',true,ARRAY['cloud'],ARRAY['PR.DS'],ARRAY[]::text[],ARRAY[]::text[]),
        ('DB-BULK-SELECT','DB Bulk Access Response','Investigate bulk DB access','alert','["db"]','{"min":"high"}','db-bulk-select-workflow',true,ARRAY['db','data'],ARRAY['DE.CM','PR.DS'],ARRAY['TA0009'],ARRAY['T1005']),
        ('DB-PUBLIC-EXPOSED','DB Public Exposure','Handle public DB exposure','finding','["db"]','{"min":"high"}','db-public-exposed-workflow',true,ARRAY['db'],ARRAY['PR.DS'],ARRAY[]::text[],ARRAY[]::text[]),
        ('DB-AUDIT-OFF','DB Audit Logging Off','Re-enable audit logging','alert','["db","hygiene"]','{"min":"high"}','db-audit-off-workflow',true,ARRAY['db','hygiene'],ARRAY['DE.CM'],ARRAY[]::text[],ARRAY[]::text[]),
        ('SECRET-EXPOSURE','Secret Exposure Response','Handle secrets found in code/logs','finding','["code","git"]','{"min":"high"}','secret-exposure-workflow',true,ARRAY['code','git'],ARRAY['PR.DS','DE.CM'],ARRAY['TA0009'],ARRAY['T1552.001']),
        ('IAC-HIGH-RISK','IaC High-Risk Misconfig','Fix high-risk IaC issues','finding','["code","iac","cloud"]','{"min":"high"}','iac-high-risk-workflow',true,ARRAY['code','iac','cloud'],ARRAY['PR.IP','PR.AC'],ARRAY[]::text[],ARRAY[]::text[]),
        ('SAST-HIGH','High-Severity SAST Finding','Triage high-sev SAST','finding','["code","app"]','{"min":"high"}','sast-high-workflow',false,ARRAY['code','app'],ARRAY['PR.IP'],ARRAY[]::text[],ARRAY[]::text[]),
        ('AI-PROMPT-INJECTION','AI Prompt Injection Response','Handle prompt injection/jailbreak','alert','["ai"]','{"min":"high"}','ai-prompt-injection-workflow',false,ARRAY['ai'],ARRAY['PR.AC','DE.CM'],ARRAY['custom'],ARRAY['prompt_injection']),
        ('AI-DATA-LEAK','AI Data Leakage Response','Handle PII/secret leakage to LLM','alert','["ai"]','{"min":"high"}','ai-data-leak-workflow',true,ARRAY['ai'],ARRAY['PR.DS','DE.CM'],ARRAY['custom'],ARRAY['data_leak']),
        ('AI-POLICY-VIOLATION','AI Policy Violation','Handle unauthorized AI use','alert','["ai"]','{"min":"medium"}','ai-policy-violation-workflow',false,ARRAY['ai'],ARRAY['PR.AC','DE.CM'],ARRAY['custom'],ARRAY['policy_violation']),
        ('LOGGING-DISABLED','Logging Disabled','Re-enable critical logging','alert','["hygiene"]','{"min":"high"}','logging-disabled-workflow',true,ARRAY['hygiene'],ARRAY['DE.CM'],ARRAY[]::text[],ARRAY[]::text[]),
        ('AGENT-OFFLINE','Agent Offline','Restore monitoring agents','alert','["hygiene","endpoint"]','{"min":"medium"}','agent-offline-workflow',false,ARRAY['hygiene','endpoint'],ARRAY['DE.CM'],ARRAY[]::text[],ARRAY[]::text[]),
        ('DRIFT-DETECTED','Config Drift Detected','Handle policy/config drift','alert','["hygiene","config"]','{"min":"low"}','drift-detected-workflow',false,ARRAY['hygiene','config'],ARRAY['PR.IP','DE.CM'],ARRAY[]::text[],ARRAY[]::text[])
    )
    INSERT INTO playbooks (key,playbook_key,name,description,target_type,category_filter,severity_filter,workflow_ref,requires_approval,is_enabled,is_builtin,tenant_id,tags,nist_controls,mitre_tactics,mitre_techniques)
    SELECT key,key,name,description,target_type,category_filter::jsonb,severity_filter::jsonb,workflow_ref,requires_approval,true,true,sys,tags,nist_controls,mitre_tactics,mitre_techniques
    FROM pb
    ON CONFLICT (playbook_key) WHERE is_builtin = true DO NOTHING;

    INSERT INTO playbooks (key,playbook_key,name,description,target_type,category_filter,severity_filter,workflow_ref,requires_approval,is_enabled,is_builtin,tenant_id,tags,nist_controls,mitre_tactics,mitre_techniques)
    SELECT key,playbook_key,name,description,target_type,category_filter,severity_filter,workflow_ref,requires_approval,true,true,demo,tags,nist_controls,mitre_tactics,mitre_techniques
    FROM playbooks
    WHERE tenant_id = sys
    ON CONFLICT (playbook_key) WHERE is_builtin = true DO NOTHING;

    -- Detection rules seed (100) -> detection_rules + detection_rule_versions
    -- metadata will carry recommended_playbook_key, rationale, controls, mitre, tags, asset_type
    WITH det(
        key,
        title,
        description,
        category,
        severity,
        source,
        recommended_playbook_key,
        recommended_rationale,
        tags,
        mitre_tactics,
        mitre_techniques,
        nist_controls,
        iso_controls,
        asset_type
    ) AS (
        VALUES
        ('ID-NEW-ADMIN','New Admin/Privileged Role Granted','Admin privileges granted to a user','identity','high','iam','ACCOUNT-COMPROMISE','New admin role assigned','["identity"]'::jsonb,'["TA0003"]'::jsonb,'["T1098"]'::jsonb,'["PR.AC","DE.CM"]'::jsonb,'["A.5","A.12"]'::jsonb,'account'),
        ('ID-PRIV-GROUP-OFFHRS','Privileged Group Change Off-hours','Priv group change outside change window','identity','high','iam','PRIV-GROUP-CHANGE','Privileged group modified off-hours','["identity"]'::jsonb,'["TA0003"]'::jsonb,'["T1098"]'::jsonb,'["PR.AC","DE.CM"]'::jsonb,'["A.5","A.12"]'::jsonb,'account'),
        ('ID-MFA-DISABLED','MFA Disabled/Downgraded','MFA removed or bypass policy created','identity','high','iam','MFA-BYPASS','MFA disabled/downgraded','["identity"]'::jsonb,'["TA0006"]'::jsonb,'["T1556"]'::jsonb,'["PR.AC","DE.CM"]'::jsonb,'["A.5","A.12"]'::jsonb,'account'),
        ('ID-NEW-ACCESS-KEY-ADMIN','New Access Key for Admin','Access key created for privileged account','identity','high','iam','ACCOUNT-COMPROMISE','New key on admin account','["identity"]'::jsonb,'["TA0003"]'::jsonb,'["T1098"]'::jsonb,'["PR.AC","DE.CM"]'::jsonb,'["A.5","A.12"]'::jsonb,'account'),
        ('ID-FAILED-LOGIN-BURST','Failed Login Burst (User)','Multiple failed logins for same user','identity','medium','iam','PASSWORD-SPRAY','Failed logins burst','["identity"]'::jsonb,'["TA0006"]'::jsonb,'["T1110"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'account'),
        ('ID-PASSWORD-SPRAY','Password Spray Detected','Multiple users failing from same IP','identity','high','iam','PASSWORD-SPRAY','Spray pattern detected','["identity"]'::jsonb,'["TA0006"]'::jsonb,'["T1110.003"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'account'),
        ('ID-IMPOSSIBLE-TRAVEL','Impossible Travel','Same user logs in from far locations quickly','identity','high','iam','ACCOUNT-COMPROMISE','Geo anomaly','["identity"]'::jsonb,'["TA0001"]'::jsonb,'["T1078"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'account'),
        ('ID-NEW-COUNTRY-ASN','Login from New Country/ASN','First login from unseen country/ASN','identity','medium','iam','ACCOUNT-COMPROMISE','New geo/ASN login','["identity"]'::jsonb,'["TA0001"]'::jsonb,'["T1078"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'account'),
        ('ID-EXCESSIVE-STS-ASSUME','Excessive Role Assumption','Unusual high number of AssumeRole','identity','medium','cloudtrail','ACCOUNT-COMPROMISE','Excessive role usage','["identity","cloud"]'::jsonb,'["TA0001"]'::jsonb,'["T1078"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'account'),
        ('ID-INACTIVE-USER-ACTIVITY','Inactive User Activity','Inactive/terminated user making calls','identity','high','iam','ACCOUNT-COMPROMISE','Activity by inactive user','["identity"]'::jsonb,'["TA0001"]'::jsonb,'["T1078"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'account'),
        ('ID-SERVICE-ACCT-NEW-LOC','Service Account New Location','Service account used from new IP/region','identity','medium','iam','ACCOUNT-COMPROMISE','Service account location anomaly','["identity"]'::jsonb,'["TA0001"]'::jsonb,'["T1078"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'account'),
        ('ID-MASS-LOCKOUTS','Multiple Account Lockouts','Many users locked in short window','identity','medium','iam','PASSWORD-SPRAY','Mass lockouts observed','["identity"]'::jsonb,'["TA0006"]'::jsonb,'["T1110"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'account'),
        ('ID-TOKEN-MISISSUE','Token Audience/Expiry Anomaly','Unexpected token audience/expiry','identity','medium','iam','MFA-BYPASS','Token misissue','["identity"]'::jsonb,'["TA0006"]'::jsonb,'["T1550"]'::jsonb,'["PR.AC","DE.CM"]'::jsonb,'["A.5","A.12"]'::jsonb,'account'),
        ('ID-REALM-CONFIG-CHANGE','Realm Config Change','Admin changed realm flows/policies','identity','high','iam','PRIV-GROUP-CHANGE','Realm configuration change','["identity"]'::jsonb,'["TA0003"]'::jsonb,'["T1098"]'::jsonb,'["PR.AC","DE.CM"]'::jsonb,'["A.5","A.12"]'::jsonb,'config'),
        ('ID-ADMIN-NO-MFA','Admin Login Without MFA','Privileged login without MFA','identity','high','iam','MFA-BYPASS','Admin logged in without MFA','["identity"]'::jsonb,'["TA0006"]'::jsonb,'["T1556"]'::jsonb,'["PR.AC","DE.CM"]'::jsonb,'["A.5","A.12"]'::jsonb,'account'),
        ('EP-AUTORUN-NEW','New Autorun/Persistence','New autorun entry detected','endpoint','medium','wazuh','ENDPOINT-ISOLATE','New persistence mechanism','["endpoint"]'::jsonb,'["TA0003"]'::jsonb,'["T1547"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'host'),
        ('EP-LOLBIN-SUSPICIOUS','Suspicious LOLBin Execution','LOLBin with suspicious args','endpoint','medium','wazuh','ENDPOINT-ISOLATE','Suspicious built-in binary use','["endpoint"]'::jsonb,'["TA0002"]'::jsonb,'["T1218"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'host'),
        ('EP-PRIV-ESC-ATTEMPT','Privilege Escalation Attempt','Privilege escalation indicators','endpoint','high','wazuh','ENDPOINT-ISOLATE','Privilege escalation attempt','["endpoint"]'::jsonb,'["TA0004"]'::jsonb,'["T1068"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'host'),
        ('EP-NEW-RISKY-LISTENER','New Listener on Risky Port','Host listening on risky port','endpoint','medium','wazuh','ENDPOINT-ISOLATE','New risky listener','["endpoint","network"]'::jsonb,'["TA0005"]'::jsonb,'["T1046","T1105"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'host'),
        ('EP-MALWARE-DETECTED','Malware Detected','AV/EDR malware detection','endpoint','high','wazuh','MALWARE-CONTAIN','Malware found on endpoint','["endpoint","malware"]'::jsonb,'["TA0002"]'::jsonb,'["T1059","T1204"]'::jsonb,'["DE.CM","RS.MI"]'::jsonb,'["A.12"]'::jsonb,'host'),
        ('EP-RANSOMWARE-PATTERN','Ransomware Pattern','Mass file encrypt/rename','endpoint','critical','wazuh','RANSOMWARE-IR','Ransomware-like behavior','["endpoint","ransomware"]'::jsonb,'["TA0040"]'::jsonb,'["T1486"]'::jsonb,'["DE.CM","RS.MI"]'::jsonb,'["A.12","A.17"]'::jsonb,'host'),
        ('EP-SCRIPT-TMP-WEBROOT','Script Run from Temp/Webroot','Script execution from tmp/webroot','endpoint','medium','wazuh','ENDPOINT-ISOLATE','Suspicious script location','["endpoint"]'::jsonb,'["TA0002"]'::jsonb,'["T1059"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'host'),
        ('EP-FIM-SYSTEM-PATH','System File Change','FIM change under critical path','endpoint','medium','wazuh','ENDPOINT-ISOLATE','System path modified','["endpoint"]'::jsonb,'["TA0005"]'::jsonb,'["T1565.001"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'host'),
        ('EP-NEW-LOCAL-USER','New Local User Created','Local user creation detected','endpoint','medium','wazuh','ENDPOINT-ISOLATE','New local account created','["endpoint"]'::jsonb,'["TA0005"]'::jsonb,'["T1136.001"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'host'),
        ('EP-FAILED-SUDO-BURST','Failed sudo/su Burst','Multiple failed privilege attempts','endpoint','medium','wazuh','ENDPOINT-ISOLATE','Failed sudo/su burst','["endpoint"]'::jsonb,'["TA0004"]'::jsonb,'["T1110"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'host'),
        ('EP-AGENT-OFFLINE','Endpoint Agent Offline','Agent stopped reporting','endpoint','medium','wazuh','AGENT-OFFLINE','Agent offline','["endpoint","hygiene"]'::jsonb, '[]'::jsonb,'[]'::jsonb,'["DE.CM"]'::jsonb,'[]'::jsonb,'host'),
        ('EP-KERNEL-TAMPER','Kernel/Driver Tampering','Kernel/driver tamper indicators','endpoint','high','wazuh','ENDPOINT-ISOLATE','Kernel tamper','["endpoint"]'::jsonb,'["TA0005"]'::jsonb,'["T1055","T1562"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'host'),
        ('EP-UNAPPROVED-SOFTWARE','Unapproved Software Installed','Package install not allowlisted','endpoint','low','wazuh','ENDPOINT-ISOLATE','Unapproved software','["endpoint"]'::jsonb,'["TA0005"]'::jsonb,'["T1195"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'host'),
        ('EP-SENSITIVE-FILE-ACCESS','Sensitive File Access','Sensitive file read by unusual user','endpoint','medium','wazuh','ENDPOINT-ISOLATE','Sensitive file accessed','["endpoint"]'::jsonb,'["TA0006"]'::jsonb,'["T1005"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'host'),
        ('EP-REMOTE-ACCESS-TOOLS','Unapproved Remote Access Tool','Remote access tool detected','endpoint','medium','wazuh','ENDPOINT-ISOLATE','Remote tool detected','["endpoint"]'::jsonb,'["TA0005"]'::jsonb,'["T1219"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'host'),
        ('NW-INBOUND-SCAN','Inbound Port Scan','Inbound scan detected','network','medium','suricata','WAF-ATTACK','Inbound scan','["network"]'::jsonb,'["TA0007"]'::jsonb,'["T1046"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'network'),
        ('NW-OUTBOUND-SCAN','Outbound Port Scan','Outbound scan/recon','network','medium','suricata','EGRESS-ANOMALY','Outbound scan','["network"]'::jsonb,'["TA0007"]'::jsonb,'["T1046"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'network'),
        ('NW-EXPLOIT-PUBLIC-SVC','Exploit Attempt on Public Service','Exploit signature on public service','network','high','suricata','WAF-ATTACK','Exploit attempt','["network"]'::jsonb,'["TA0001"]'::jsonb,'["T1190"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'network'),
        ('NW-OUTBOUND-MALICIOUS','Outbound to Malicious Destination','Connection to known bad IP/domain','network','high','suricata','C2/BEACON','Outbound to malicious','["network"]'::jsonb,'["TA0011"]'::jsonb,'["T1071"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'network'),
        ('NW-SUSPICIOUS-DNS','Suspicious DNS','DGA/tunnel-like DNS','network','medium','suricata','C2/BEACON','Suspicious DNS','["network"]'::jsonb,'["TA0011"]'::jsonb,'["T1071.004"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'network'),
        ('NW-CLEARTEXT-PROD','Cleartext Protocol in Prod','Cleartext traffic to/from prod','network','medium','suricata','EGRESS-ANOMALY','Cleartext in prod','["network","cloud"]'::jsonb,'["TA0005"]'::jsonb,'["T1040"]'::jsonb,'["DE.CM"]'::jsonb,'["A.13"]'::jsonb,'network'),
        ('NW-NEW-EXTERNAL-EXPOSURE','New External Exposure','New inbound traffic on risky port','network','high','suricata','WAF-ATTACK','New exposure detected','["network"]'::jsonb,'["TA0007"]'::jsonb,'["T1046"]'::jsonb,'["DE.CM"]'::jsonb,'["A.13"]'::jsonb,'network'),
        ('NW-LARGE-EGRESS-NEW-IP','Large Egress to New IP','Large data transfer to new dest','network','high','flowlogs','EGRESS-ANOMALY','Large egress','["network","cloud"]'::jsonb,'["TA0010"]'::jsonb,'["T1041"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'network'),
        ('NW-MULTI-AUTH-FAIL-SRCIP','Multi-User Auth Failures','Many auth fails from one IP','network','medium','suricata','WAF-ATTACK','Auth failures same IP','["network"]'::jsonb,'["TA0006"]'::jsonb,'["T1110"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'network'),
        ('NW-VPN-ANOMALY','VPN Anomaly','Unusual VPN pattern','network','medium','vpn','ACCOUNT-COMPROMISE','VPN anomaly','["network","identity"]'::jsonb,'["TA0001"]'::jsonb,'["T1078"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'network'),
        ('NW-C2-SIGNATURE','C2 Signature','C2 family signature hit','network','high','suricata','C2/BEACON','C2 signature','["network"]'::jsonb,'["TA0011"]'::jsonb,'["T1071"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'network'),
        ('NW-TOR-PROXY','Tor/Proxy Usage','Connection to Tor/proxy','network','medium','suricata','C2/BEACON','Tor/proxy observed','["network"]'::jsonb,'["TA0011"]'::jsonb,'["T1090"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'network'),
        ('NW-LATERAL-SMB-RDP','Lateral SMB/RDP','Internal lateral movement','network','high','suricata','ENDPOINT-ISOLATE','Lateral movement','["network","endpoint"]'::jsonb,'["TA0008"]'::jsonb,'["T1021"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'network'),
        ('NW-TLS-CERT-ANOMALY','TLS Certificate Anomaly','Self-signed/mismatched cert','network','medium','suricata','WAF-ATTACK','TLS anomaly','["network"]'::jsonb,'["TA0005"]'::jsonb,'["T1553"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'network'),
        ('NW-SG-OPEN-CRITICAL','Open SG on Critical Ports','SG allows 0.0.0.0/0 on critical ports','network','high','cloudtrail','SG-OPEN-CRITICAL','Open SG detected','["network","cloud"]'::jsonb,'["TA0007"]'::jsonb,'["T1046"]'::jsonb,'["PR.AC","PR.DS"]'::jsonb,'["A.13","A.18"]'::jsonb,'network'),
        ('CLD-PUBLIC-STORAGE','Public Storage','Bucket/blob publicly accessible','cloud','high','prowler','CLOUD-PUBLIC-STORAGE','Public storage','["cloud","posture"]'::jsonb,'[]'::jsonb,'[]'::jsonb,'["PR.DS","DE.CM"]'::jsonb,'["A.8","A.13"]'::jsonb,'cloud_resource'),
        ('CLD-STORAGE-PII-UNENCRYPTED','Storage PII Unencrypted/Public','PII storage unencrypted/public','cloud','high','prowler','CLOUD-PUBLIC-STORAGE','PII storage risk','["cloud","posture"]'::jsonb,'[]'::jsonb,'[]'::jsonb,'["PR.DS","DE.CM"]'::jsonb,'["A.8","A.13"]'::jsonb,'cloud_resource'),
        ('CLD-EXCESSIVE-GET-LIST','Excessive Storage Access','Excessive GET/LIST on sensitive bucket','cloud','high','cloudtrail','EGRESS-ANOMALY','Possible exfiltration','["cloud","data"]'::jsonb,'["TA0010"]'::jsonb,'["T1041"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'cloud_resource'),
        ('CLD-SG-OPEN-SENSITIVE','Open SG Sensitive','SG open on sensitive ports','cloud','high','cloudtrail','SG-OPEN-CRITICAL','Open SG','["cloud","network"]'::jsonb,'["TA0007"]'::jsonb,'["T1046"]'::jsonb,'["PR.AC","PR.DS"]'::jsonb,'["A.13","A.18"]'::jsonb,'cloud_resource'),
        ('CLD-ROOT-USE','Root/Break-glass Use','Root account usage','cloud','high','cloudtrail','ROOT-USE','Root used','["cloud","identity"]'::jsonb,'["TA0001"]'::jsonb,'["T1078"]'::jsonb,'["PR.AC","DE.CM"]'::jsonb,'["A.5","A.12"]'::jsonb,'account'),
        ('CLD-NEW-PRIV-ROLE','New Privileged Role/Policy','New high-priv role/policy attached','cloud','high','cloudtrail','PRIV-GROUP-CHANGE','New privileged role','["cloud","identity"]'::jsonb,'["TA0003"]'::jsonb,'["T1098"]'::jsonb,'["PR.AC"]'::jsonb,'["A.5","A.12"]'::jsonb,'account'),
        ('CLD-CHANGE-NO-TICKET','Change Without Ticket','Critical change lacking ticket tag','cloud','medium','cloudtrail','DRIFT-DETECTED','No ticket/change ref','["cloud","config"]'::jsonb,'["TA0005"]'::jsonb,'["T1098"]'::jsonb,'["PR.IP"]'::jsonb,'["A.12","A.18"]'::jsonb,'config'),
        ('CLD-K8S-CLUSTER-ADMIN','K8s Cluster-Admin Binding','Clusterrolebinding granting cluster-admin','cloud','high','k8s','K8S-PRIV-POD','Cluster-admin granted','["cloud","k8s"]'::jsonb,'["TA0003"]'::jsonb,'["T1098"]'::jsonb,'["PR.AC"]'::jsonb,'["A.14"]'::jsonb,'k8s_cluster'),
        ('CLD-K8S-PRIV-POD','K8s Privileged Pod','Pod runs privileged/hostPID/hostNet','cloud','high','k8s','K8S-PRIV-POD','Privileged pod','["cloud","k8s"]'::jsonb,'["TA0004"]'::jsonb,'["T1548"]'::jsonb,'["PR.AC"]'::jsonb,'["A.14"]'::jsonb,'k8s_cluster'),
        ('CLD-UNAPPROVED-REGISTRY','Unapproved Image Registry','Image pulled from unapproved registry','cloud','medium','k8s','K8S-PRIV-POD','Unapproved registry','["cloud","k8s"]'::jsonb,'["TA0005"]'::jsonb,'["T1195"]'::jsonb,'["PR.AC"]'::jsonb,'["A.14"]'::jsonb,'k8s_cluster'),
        ('CLD-NEW-EXTERNAL-PRINCIPAL','New External Principal Granted','External principal given access','cloud','medium','cloudtrail','ACCOUNT-COMPROMISE','External principal granted','["cloud"]'::jsonb,'["TA0001"]'::jsonb,'["T1078"]'::jsonb,'["PR.AC"]'::jsonb,'["A.13"]'::jsonb,'account'),
        ('CLD-MASS-DELETE-STOP','Mass Delete/Stop Resources','Mass resource deletions/stops','cloud','high','cloudtrail','RANSOMWARE-IR','Mass delete/stop','["cloud"]'::jsonb,'["TA0040"]'::jsonb,'["T1529"]'::jsonb,'["RS.MI"]'::jsonb,'["A.17"]'::jsonb,'cloud_resource'),
        ('CLD-CLOUDTRAIL-DISABLED','CloudTrail Disabled/Tampered','Trail/config logging disabled','cloud','high','cloudtrail','LOGGING-DISABLED','Logging disabled','["cloud","hygiene"]'::jsonb,'["TA0005"]'::jsonb,'["T1562"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12","A.18"]'::jsonb,'config'),
        ('CLD-KMS-KEY-DISABLE-DELETE','KMS Key Disable/Delete','KMS key disabled or scheduled delete','cloud','high','cloudtrail','KMS-KEY-DISABLED','KMS key impacted','["cloud"]'::jsonb,'["TA0040"]'::jsonb,'["T1485"]'::jsonb,'["PR.DS"]'::jsonb,'["A.10","A.18"]'::jsonb,'cloud_resource'),
        ('CLD-NEW-REGION-ACTIVITY','New Region Activity','New region activity for tenant','cloud','medium','cloudtrail','ACCOUNT-COMPROMISE','New region used','["cloud"]'::jsonb,'["TA0001"]'::jsonb,'["T1078"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'cloud_resource'),
        ('DB-PUBLIC-PROD','DB Public in Prod','Prod DB publicly accessible','db','high','prowler','DB-PUBLIC-EXPOSED','Public DB exposure','["db"]'::jsonb,'["TA0009"]'::jsonb,'["T1530"]'::jsonb,'["PR.DS"]'::jsonb,'["A.8","A.13"]'::jsonb,'db_instance'),
        ('DB-UNENCRYPTED-STORAGE','DB Unencrypted Storage/Snapshots','Unencrypted DB storage or snapshots','db','high','prowler','DB-PUBLIC-EXPOSED','Unencrypted DB storage','["db"]'::jsonb,'["TA0009"]'::jsonb,'["T1530"]'::jsonb,'["PR.DS"]'::jsonb,'["A.8","A.10"]'::jsonb,'db_instance'),
        ('DB-BULK-SELECT-SENSITIVE','Bulk SELECT Sensitive Table','Bulk SELECT on sensitive tables','db','high','dbaudit','DB-BULK-SELECT','Bulk DB access','["db","data"]'::jsonb,'["TA0009"]'::jsonb,'["T1005"]'::jsonb,'["DE.CM","PR.DS"]'::jsonb,'["A.8","A.12"]'::jsonb,'db_instance'),
        ('DB-SVC-ACCOUNT-ANOMALY','Service Account DB Anomaly','Service account unusual access','db','medium','dbaudit','DB-BULK-SELECT','Anomalous DB access','["db"]'::jsonb,'["TA0001"]'::jsonb,'["T1078"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'db_instance'),
        ('DB-SCHEMA-CHANGE-NONDBA','Schema Change by Non-DBA','DDL in prod by non-DBA','db','high','dbaudit','DB-BULK-SELECT','Unauthorized schema change','["db"]'::jsonb,'["TA0040"]'::jsonb,'["T1491"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12","A.14"]'::jsonb,'db_instance'),
        ('DB-MASS-DELETE-UPDATE','Mass Delete/Update Sensitive','Mass destructive queries','db','high','dbaudit','DB-BULK-SELECT','Mass data modification','["db"]'::jsonb,'["TA0040"]'::jsonb,'["T1499"]'::jsonb,'["DE.CM","RS.MI"]'::jsonb,'["A.12","A.17"]'::jsonb,'db_instance'),
        ('DB-FAILED-LOGINS-BURST','DB Failed Logins Burst','Many DB login failures','db','medium','dbaudit','DB-BULK-SELECT','DB auth failures burst','["db"]'::jsonb,'["TA0006"]'::jsonb,'["T1110"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'db_instance'),
        ('DB-ACCOUNT-CREATED-PROD','DB Account Created in Prod','New DB account in prod','db','high','dbaudit','DB-BULK-SELECT','New DB account','["db"]'::jsonb,'["TA0003"]'::jsonb,'["T1098"]'::jsonb,'["PR.AC"]'::jsonb,'["A.5","A.12"]'::jsonb,'db_instance'),
        ('DB-AUDIT-LOG-OFF','DB Audit Logging Off','DB audit log disabled','db','high','dbaudit','DB-AUDIT-OFF','Audit disabled','["db","hygiene"]'::jsonb,'["TA0005"]'::jsonb,'["T1562"]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'db_instance'),
        ('DB-NEW-HOST-ACCESS','DB Access from New Host/IP','DB accessed from new host/IP','db','medium','dbaudit','DB-BULK-SELECT','New DB client host','["db"]'::jsonb,'["TA0001"]'::jsonb,'["T1078"]'::jsonb,'["DE.CM"]'::jsonb,'["A.13"]'::jsonb,'db_instance'),
        ('GIT-SECRET-FOUND','Secrets Found in Code','Secret in repo detected','code','high','scanner','SECRET-EXPOSURE','Secret exposed in code','["code","git"]'::jsonb,'["TA0009"]'::jsonb,'["T1552.001"]'::jsonb,'["PR.DS","DE.CM"]'::jsonb,'["A.9","A.12"]'::jsonb,'repo'),
        ('GIT-IAC-HIGH-RISK','High-Risk IaC Misconfig','High-risk IaC issue','code','high','scanner','IAC-HIGH-RISK','High-risk IaC finding','["code","iac","cloud"]'::jsonb,'["TA0042"]'::jsonb,'["T1587"]'::jsonb,'["PR.IP","PR.AC"]'::jsonb,'["A.14"]'::jsonb,'repo'),
        ('GIT-HARD-CODED-KEYS','Hard-coded Keys','Hard-coded keys in code','code','high','scanner','SECRET-EXPOSURE','Hard-coded key found','["code","git"]'::jsonb,'["TA0009"]'::jsonb,'["T1552.001"]'::jsonb,'["PR.DS"]'::jsonb,'["A.9","A.12"]'::jsonb,'repo'),
        ('GIT-PRIV-IAM-IAC','Privileged IAM in IaC','Over-privileged IAM in IaC','code','high','scanner','IAC-HIGH-RISK','IAM over-privilege in IaC','["code","iac"]'::jsonb,'["TA0003"]'::jsonb,'["T1098"]'::jsonb,'["PR.AC"]'::jsonb,'["A.5","A.12"]'::jsonb,'repo'),
        ('CI-TOKEN-LEAK-LOGS','CI Token/Secret in Logs','Token/secret leak in CI logs','code','high','ci','SECRET-EXPOSURE','Secret in CI logs','["code","ci"]'::jsonb,'["TA0009"]'::jsonb,'["T1552.001"]'::jsonb,'["PR.DS"]'::jsonb,'["A.12"]'::jsonb,'repo'),
        ('GIT-K8S-MANIFEST-RISK','Insecure K8s Manifest','K8s manifest risky settings','code','medium','scanner','IAC-HIGH-RISK','Risky k8s manifest','["code","k8s"]'::jsonb,'["TA0042"]'::jsonb,'["T1609"]'::jsonb,'["PR.IP"]'::jsonb,'["A.14"]'::jsonb,'repo'),
        ('GIT-SAST-HIGH','High-Severity SAST Finding','High-sev SAST issue','code','high','scanner','SAST-HIGH','High SAST finding','["code","app"]'::jsonb,'[]'::jsonb,'[]'::jsonb,'["PR.IP"]'::jsonb,'["A.14"]'::jsonb,'repo'),
        ('GIT-SENSITIVE-FILE','Sensitive File Committed','Sensitive file committed (.pem/db)','code','medium','scanner','SECRET-EXPOSURE','Sensitive file in repo','["code","git"]'::jsonb,'["TA0009"]'::jsonb,'["T1552.001"]'::jsonb,'["PR.DS"]'::jsonb,'["A.9"]'::jsonb,'repo'),
        ('GIT-NO-BRANCH-PROTECTION','No Branch Protection','Repo without branch protection','code','low','scm','DRIFT-DETECTED','Branch protection missing','["code","git"]'::jsonb,'["TA0042"]'::jsonb,'["T1609"]'::jsonb,'["PR.AC"]'::jsonb,'["A.14"]'::jsonb,'repo'),
        ('CI-BYPASS-CHECKS','CI Bypass Checks','Pipeline step altered to bypass checks','code','medium','ci','DRIFT-DETECTED','Checks bypassed','["code","ci"]'::jsonb,'["TA0005"]'::jsonb,'["T1553"]'::jsonb,'["PR.IP"]'::jsonb,'["A.14"]'::jsonb,'repo'),
        ('AI-PROMPT-INJECTION-DET','AI Prompt Injection Detected','Prompt injection/jailbreak pattern','ai','high','ai_gateway','AI-PROMPT-INJECTION','Prompt injection detected','["ai"]'::jsonb,'["custom"]'::jsonb,'["prompt_injection"]'::jsonb,'["PR.AC","DE.CM"]'::jsonb,'["A.14"]'::jsonb,'ai_app'),
        ('AI-DATA-LEAKAGE','AI Data Leakage','PII/secret leakage to LLM','ai','high','ai_gateway','AI-DATA-LEAK','AI data leakage','["ai"]'::jsonb,'["custom"]'::jsonb,'["data_leak"]'::jsonb,'["PR.DS","DE.CM"]'::jsonb,'["A.14","A.18"]'::jsonb,'ai_app'),
        ('AI-POLICY-VIOLATION','AI Policy Violation','Unauthorized AI use','ai','medium','ai_gateway','AI-POLICY-VIOLATION','AI policy violation','["ai"]'::jsonb,'["custom"]'::jsonb,'["policy_violation"]'::jsonb,'["PR.AC","DE.CM"]'::jsonb,'["A.5","A.14"]'::jsonb,'ai_app'),
        ('AI-TOOL-CALL-ANOMALY','AI Tool Call Anomaly','Abnormal tool-call pattern','ai','medium','ai_gateway','AI-POLICY-VIOLATION','Tool-call anomaly','["ai"]'::jsonb,'["custom"]'::jsonb,'["tool_anomaly"]'::jsonb,'["PR.AC","DE.CM"]'::jsonb,'["A.14"]'::jsonb,'ai_app'),
        ('AI-EXCESSIVE-TOKENS','AI Excessive Tokens/Requests','Excessive tokens/requests anomaly','ai','medium','ai_gateway','AI-POLICY-VIOLATION','Usage anomaly','["ai"]'::jsonb,'["custom"]'::jsonb,'["usage_anomaly"]'::jsonb,'["DE.CM"]'::jsonb,'["A.14"]'::jsonb,'ai_app'),
        ('AI-NEW-APP-UNREGISTERED','Unregistered AI App','New AI app/client unregistered','ai','medium','ai_gateway','AI-POLICY-VIOLATION','Unregistered AI app','["ai"]'::jsonb,'["custom"]'::jsonb,'["unauthorized_app"]'::jsonb,'["PR.AC"]'::jsonb,'["A.14"]'::jsonb,'ai_app'),
        ('AI-ENDPOINT-NEW-REGION','AI Endpoint New Region/IP','Model endpoint used from new region/IP','ai','medium','ai_gateway','AI-POLICY-VIOLATION','New region/IP for AI','["ai"]'::jsonb,'["custom"]'::jsonb,'["geo_anomaly"]'::jsonb,'["DE.CM"]'::jsonb,'["A.13","A.14"]'::jsonb,'ai_app'),
        ('AI-JAILBREAK-BURST','AI Jailbreak Burst','Burst of jailbreak attempts','ai','high','ai_gateway','AI-PROMPT-INJECTION','Jailbreak burst','["ai"]'::jsonb,'["custom"]'::jsonb,'["prompt_injection"]'::jsonb,'["PR.AC","DE.CM"]'::jsonb,'["A.14"]'::jsonb,'ai_app'),
        ('AI-UNSAFE-TOOL-ACTION','Unsafe Tool Action','Unsafe tool invocation','ai','high','ai_gateway','AI-POLICY-VIOLATION','Unsafe tool call','["ai"]'::jsonb,'["custom"]'::jsonb,'["unsafe_tool"]'::jsonb,'["PR.AC","DE.CM"]'::jsonb,'["A.14"]'::jsonb,'ai_app'),
        ('AI-GATEWAY-CONFIG-CHANGE','AI Gateway Config Change','Gateway config changed','ai','medium','ai_gateway','DRIFT-DETECTED','AI gateway config change','["ai","config"]'::jsonb,'["custom"]'::jsonb,'["config_change"]'::jsonb,'["PR.IP","DE.CM"]'::jsonb,'["A.12","A.14"]'::jsonb,'config'),
        ('HG-LOGGING-DISABLED','Logging Disabled','Critical logging disabled','hygiene','high','config','LOGGING-DISABLED','Logging disabled','["hygiene"]'::jsonb,'[]'::jsonb,'[]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'config'),
        ('HG-SIEM-PIPELINE-STALLED','SIEM Pipeline Stalled','Ingestion stalled','hygiene','medium','siem','LOGGING-DISABLED','SIEM pipeline stalled','["hygiene"]'::jsonb,'[]'::jsonb,'[]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'config'),
        ('HG-AGENT-OUTDATED','Agent Outdated','Agents out of date','hygiene','medium','config','AGENT-OFFLINE','Agents outdated','["hygiene","endpoint"]'::jsonb,'[]'::jsonb,'[]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'config'),
        ('HG-BACKUP-FAILURES','Backup Failures','Repeated backup failures','hygiene','medium','backup','DRIFT-DETECTED','Backups failing','["hygiene"]'::jsonb,'[]'::jsonb,'[]'::jsonb,'["PR.IP"]'::jsonb,'["A.17"]'::jsonb,'config'),
        ('HG-CERT-EXPIRING','Certificate Expiring','Cert expiring soon','hygiene','low','cert','DRIFT-DETECTED','Certificate expiring','["hygiene"]'::jsonb,'[]'::jsonb,'[]'::jsonb,'["PR.DS"]'::jsonb,'["A.10","A.18"]'::jsonb,'cert'),
        ('HG-TIME-DRIFT','Time Drift','Time sync drift detected','hygiene','low','config','DRIFT-DETECTED','Time drift','["hygiene"]'::jsonb,'[]'::jsonb,'[]'::jsonb,'["PR.IP"]'::jsonb,'["A.12"]'::jsonb,'config'),
        ('HG-POLICY-DRIFT','Policy/Config Drift','Policy/config drift detected','hygiene','medium','config','DRIFT-DETECTED','Policy drift','["hygiene"]'::jsonb,'[]'::jsonb,'[]'::jsonb,'["PR.IP","DE.CM"]'::jsonb,'["A.12","A.18"]'::jsonb,'config'),
        ('HG-NO-DETECTIONS-LONG','No Detections Long Window','Unusual silence from detections','hygiene','low','siem','LOGGING-DISABLED','No detections observed','["hygiene"]'::jsonb,'[]'::jsonb,'[]'::jsonb,'["DE.CM"]'::jsonb,'["A.12"]'::jsonb,'config'),
        ('HG-TICKETING-WEBHOOK-FAIL','Ticketing/Webhook Failures','Ticket/webhook delivery failing','hygiene','medium','ticketing','EXEC-NOTIFY','Ticket/webhook failing','["hygiene"]'::jsonb,'[]'::jsonb,'[]'::jsonb,'["RS.CO"]'::jsonb,'["A.16"]'::jsonb,'config'),
        ('HG-CONNECTOR-MISSING','Missing Required Connector','Required connector missing','hygiene','medium','config','DRIFT-DETECTED','Connector missing','["hygiene","onboarding"]'::jsonb,'[]'::jsonb,'[]'::jsonb,'["PR.IP"]'::jsonb,'["A.12"]'::jsonb,'config')
    ),
    ins_rules AS (
        INSERT INTO detection_rules (rule_key,name,description,category,current_version,is_builtin,tenant_id)
        SELECT key,title,description,category,'v1',true,sys FROM det
        ON CONFLICT (rule_key) DO NOTHING
        RETURNING rule_key,id
    ), all_rules AS (
        SELECT rule_key,id FROM detection_rules WHERE tenant_id = sys
    )
    INSERT INTO detection_rule_versions (rule_id,version,index_pattern,query,trigger_condition,severity,action_config,metadata)
    SELECT r.id,'v1','alerts-*','{"match_all":{}}'::jsonb,'{"type":"threshold","threshold":1}'::jsonb,
           d.severity,
           '{}'::jsonb,
           jsonb_build_object(
               'recommended_playbook_key', d.recommended_playbook_key,
               'recommended_rationale', d.recommended_rationale,
               'tags', d.tags::jsonb,
               'asset_type', d.asset_type,
               'nist_controls', d.nist_controls,
               'iso_27001', d.iso_controls,
               'mitre_tactics', d.mitre_tactics,
               'mitre_techniques', d.mitre_techniques
           )
    FROM det d
    JOIN all_rules r ON r.rule_key = d.key
    ON CONFLICT (rule_id, version) DO NOTHING;

    -- Clone detection_rules to demo
    WITH src AS (
        SELECT rule_key,name,description,category,current_version,is_builtin FROM detection_rules WHERE tenant_id = sys
    ), ins_demo AS (
        INSERT INTO detection_rules (rule_key,name,description,category,current_version,is_builtin,tenant_id)
        SELECT rule_key,name,description,category,current_version,is_builtin,demo FROM src
        ON CONFLICT (rule_key) DO NOTHING
        RETURNING rule_key,id
    ), demo_rules AS (
        SELECT rule_key,id FROM detection_rules WHERE tenant_id = demo
    ), src_versions AS (
        SELECT dr.rule_key, drv.version, drv.index_pattern, drv.query, drv.trigger_condition, drv.severity, drv.action_config, drv.metadata
        FROM detection_rules dr
        JOIN detection_rule_versions drv ON drv.rule_id = dr.id
        WHERE dr.tenant_id = sys
    )
    INSERT INTO detection_rule_versions (rule_id,version,index_pattern,query,trigger_condition,severity,action_config,metadata)
    SELECT d.id, sv.version, sv.index_pattern, sv.query, sv.trigger_condition, sv.severity, sv.action_config, sv.metadata
    FROM src_versions sv
    JOIN demo_rules d ON d.rule_key = sv.rule_key
    ON CONFLICT (rule_id, version) DO NOTHING;
END $$;
