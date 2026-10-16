-- Migration: 042 - Seed Alarm Templates
-- Purpose: Preload alarm templates for the no-code SIEM editor.

WITH defs AS (
    SELECT * FROM (VALUES
        ('SG-DET-001', 'Suspicious Login / Account Takeover', 'Detect suspicious login patterns (fails then success)', 'identity', 'high', 'suspicious_login', 'PLAYBOOK_ACCOUNT_TAKEOVER'),
        ('SG-DET-002', 'User-Reported Phishing', 'User reports suspicious email', 'email', 'medium', 'phishing_user_report', 'PLAYBOOK_PHISHING_USER_REPORTED'),
        ('SG-DET-003', 'Email Security Phishing Campaign', 'Email gateway flags high-severity phishing', 'email', 'high', 'phishing_campaign', 'PLAYBOOK_EMAIL_CAMPAIGN'),
        ('SG-DET-004', 'Endpoint Malware Detection', 'High-severity malware on endpoint', 'endpoint', 'high', 'endpoint_malware', 'PLAYBOOK_ENDPOINT_MALWARE'),
        ('SG-DET-005', 'Ransomware Suspected', 'Ransomware family detected/suspected', 'endpoint', 'critical', 'ransomware_suspected', 'PLAYBOOK_RANSOMWARE'),
        ('SG-DET-006', 'Public Cloud Storage Misconfiguration', 'Public S3/GCS bucket', 'cloud', 'high', 'public_bucket', 'PLAYBOOK_PUBLIC_BUCKET'),
        ('SG-DET-007', 'Privilege Escalation', 'Admin role grant or escalation', 'identity', 'high', 'privilege_escalation', 'PLAYBOOK_PRIV_ESC'),
        ('SG-DET-008', 'Password Spray', 'High-volume auth failures across users', 'identity', 'high', 'password_spray', 'PLAYBOOK_PASSWORD_SPRAY'),
        ('SG-DET-009', 'Data Exfiltration', 'Large outbound data transfer', 'network', 'critical', 'data_exfil', 'PLAYBOOK_DATA_EXFIL'),
        ('SG-DET-010', 'Lost Device', 'Reported lost/stolen device', 'device', 'medium', 'lost_device', 'PLAYBOOK_LOST_DEVICE')
    ) AS t(rule_key, name, description, category, severity, alert_type, playbook_key)
)
-- Insert detection_rules if missing
INSERT INTO detection_rules (rule_key, name, description, category, current_version, is_builtin, created_by)
SELECT d.rule_key, d.name, d.description, d.category, '1.0.0', true, 'migration_042'
FROM defs d
ON CONFLICT (rule_key) DO NOTHING;

-- Insert detection_rule_versions as template placeholders if missing
WITH defs AS (
    SELECT * FROM (VALUES
        ('SG-DET-001', 'Suspicious Login / Account Takeover', 'Detect suspicious login patterns (fails then success)', 'identity', 'high', 'suspicious_login', 'PLAYBOOK_ACCOUNT_TAKEOVER'),
        ('SG-DET-002', 'User-Reported Phishing', 'User reports suspicious email', 'email', 'medium', 'phishing_user_report', 'PLAYBOOK_PHISHING_USER_REPORTED'),
        ('SG-DET-003', 'Email Security Phishing Campaign', 'Email gateway flags high-severity phishing', 'email', 'high', 'phishing_campaign', 'PLAYBOOK_EMAIL_CAMPAIGN'),
        ('SG-DET-004', 'Endpoint Malware Detection', 'High-severity malware on endpoint', 'endpoint', 'high', 'endpoint_malware', 'PLAYBOOK_ENDPOINT_MALWARE'),
        ('SG-DET-005', 'Ransomware Suspected', 'Ransomware family detected/suspected', 'endpoint', 'critical', 'ransomware_suspected', 'PLAYBOOK_RANSOMWARE'),
        ('SG-DET-006', 'Public Cloud Storage Misconfiguration', 'Public S3/GCS bucket', 'cloud', 'high', 'public_bucket', 'PLAYBOOK_PUBLIC_BUCKET'),
        ('SG-DET-007', 'Privilege Escalation', 'Admin role grant or escalation', 'identity', 'high', 'privilege_escalation', 'PLAYBOOK_PRIV_ESC'),
        ('SG-DET-008', 'Password Spray', 'High-volume auth failures across users', 'identity', 'high', 'password_spray', 'PLAYBOOK_PASSWORD_SPRAY'),
        ('SG-DET-009', 'Data Exfiltration', 'Large outbound data transfer', 'network', 'critical', 'data_exfil', 'PLAYBOOK_DATA_EXFIL'),
        ('SG-DET-010', 'Lost Device', 'Reported lost/stolen device', 'device', 'medium', 'lost_device', 'PLAYBOOK_LOST_DEVICE')
    ) AS t(rule_key, name, description, category, severity, alert_type, playbook_key)
)
INSERT INTO detection_rule_versions (
    rule_id, version, index_pattern, query, trigger_condition, severity,
    action_config, metadata, changelog, is_active, is_template, created_by
)
SELECT
    dr.id,
    '1.0.0',
    'sg-{tenant_id}-*',
    -- Minimal match-all query; users will edit via no-code editor
    '{"size":0,"query":{"match_all":{}}}',
    -- Trigger if any doc exists; users will adjust thresholds
    '{"script":{"source":"return ctx.results[0].hits.total.value > 0;"}}',
    d.severity,
    jsonb_build_object('auto_execute', false, 'playbook_key', d.playbook_key),
    jsonb_build_object(
        'alert_type', d.alert_type,
        'category', d.category,
        'template', true
    ),
    'Seeded template',
    true,
    true,
    'migration_042'
FROM defs d
JOIN detection_rules dr ON dr.rule_key = d.rule_key
ON CONFLICT (rule_id, version) DO NOTHING;

-- Mark seeded versions as templates
UPDATE detection_rule_versions
SET is_template = true
WHERE rule_id IN (SELECT id FROM detection_rules WHERE rule_key LIKE 'SG-DET-%');
