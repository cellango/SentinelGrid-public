-- Migration: Seed Out-of-the-Box (OOTB) Playbooks
-- Date: 2025-12-03
-- Purpose: Add default playbook templates for common security incidents

-- Note: These are system-level playbooks (no tenant_id initially)
-- Tenants can clone them via the UI

-- Create a system tenant for built-in playbooks if it doesn't exist
INSERT INTO tenants (id, name, slug, status)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'SentinelGrid System',
    'system',
    'active'
) ON CONFLICT (id) DO NOTHING;

-- 1. Phishing – User Reported
INSERT INTO playbooks (
    id, tenant_id, key, name, description, target_type,
    severity_filter, category_filter, workflow_ref,
    requires_approval, is_enabled, is_builtin
)
VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000000',
    'PHISH-USER-REPORTED-v1',
    'Phishing – User Reported',
    'Handle user-reported phishing emails: analyze, quarantine, notify',
    'alert',
    '{"min": "medium"}'::jsonb,
    '["phishing"]'::jsonb,
    'phish-user-reported-workflow',
    true,
    true,
    true
) ON CONFLICT DO NOTHING;

-- 2. Phishing – Email Security Alert
INSERT INTO playbooks (
    id, tenant_id, key, name, description, target_type,
    severity_filter, category_filter, workflow_ref,
    requires_approval, is_enabled, is_builtin
)
VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000000',
    'PHISH-GATEWAY-ALERT-v1',
    'Phishing – Email Security Alert',
    'Respond to email gateway/SEG phishing detections',
    'alert',
    '{"min": "high"}'::jsonb,
    '["phishing"]'::jsonb,
    'phish-gateway-workflow',
    false,
    true,
    true
) ON CONFLICT DO NOTHING;

-- 3. Account Compromise / Suspicious Login
INSERT INTO playbooks (
    id, tenant_id, key, name, description, target_type,
    severity_filter, category_filter, workflow_ref,
    requires_approval, is_enabled, is_builtin
)
VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000000',
    'ID-ACCOUNT-COMPROMISE-v1',
    'Account Compromise / Suspicious Login',
    'Investigate and contain suspicious login activity or account takeover',
    'alert',
    '{"min": "medium"}'::jsonb,
    '["identity"]'::jsonb,
    'account-compromise-workflow',
    true,
    true,
    true
) ON CONFLICT DO NOTHING;

-- 4. Password Spray / Brute Force Attack
INSERT INTO playbooks (
    id, tenant_id, key, name, description, target_type,
    severity_filter, category_filter, workflow_ref,
    requires_approval, is_enabled, is_builtin
)
VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000000',
    'ID-PASSWORD-SPRAY-v1',
    'Password Spray / Brute Force Attack',
    'Respond to password spray or brute force attempts',
    'alert',
    '{"min": "high"}'::jsonb,
    '["identity"]'::jsonb,
    'password-spray-workflow',
    false,
    true,
    true
) ON CONFLICT DO NOTHING;

-- 5. Malware – Endpoint Infection
INSERT INTO playbooks (
    id, tenant_id, key, name, description, target_type,
    severity_filter, category_filter, workflow_ref,
    requires_approval, is_enabled, is_builtin
)
VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000000',
    'MAL-GENERIC-ENDPOINT-v1',
    'Malware – Endpoint Infection',
    'Isolate and remediate malware detected on endpoints',
    'alert',
    '{"min": "high"}'::jsonb,
    '["malware"]'::jsonb,
    'malware-endpoint-workflow',
    true,
    true,
    true
) ON CONFLICT DO NOTHING;

-- 6. Ransomware – Suspected / Confirmed
INSERT INTO playbooks (
    id, tenant_id, key, name, description, target_type,
    severity_filter, category_filter, workflow_ref,
    requires_approval, is_enabled, is_builtin
)
VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000000',
    'MAL-RANSOMWARE-v1',
    'Ransomware – Suspected / Confirmed',
    'Emergency containment and recovery for ransomware incidents',
    'alert',
    '{"min": "critical"}'::jsonb,
    '["malware", "ransomware"]'::jsonb,
    'ransomware-workflow',
    false,
    true,
    true
) ON CONFLICT DO NOTHING;

-- 7. Cloud – Public Storage Misconfiguration
INSERT INTO playbooks (
    id, tenant_id, key, name, description, target_type,
    severity_filter, category_filter, workflow_ref,
    requires_approval, is_enabled, is_builtin
)
VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000000',
    'CSPM-PUBLIC-STORAGE-v1',
    'Cloud – Public Storage Misconfiguration',
    'Remediate publicly exposed S3/Azure Blob/GCS buckets',
    'finding',
    '{"min": "high"}'::jsonb,
    '["posture", "cloud"]'::jsonb,
    'public-storage-workflow',
    true,
    true,
    true
) ON CONFLICT DO NOTHING;

-- 8. Cloud – Suspicious API Activity
INSERT INTO playbooks (
    id, tenant_id, key, name, description, target_type,
    severity_filter, category_filter, workflow_ref,
    requires_approval, is_enabled, is_builtin
)
VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000000',
    'CLOUD-SUSPICIOUS-API-v1',
    'Cloud – Suspicious API Activity',
    'Investigate unusual cloud API calls or privilege escalation',
    'alert',
    '{"min": "medium"}'::jsonb,
    '["cloud"]'::jsonb,
    'cloud-api-workflow',
    true,
    true,
    true
) ON CONFLICT DO NOTHING;

-- 9. Data Exfiltration / Unusual Downloads
INSERT INTO playbooks (
    id, tenant_id, key, name, description, target_type,
    severity_filter, category_filter, workflow_ref,
    requires_approval, is_enabled, is_builtin
)
VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000000',
    'DATA-EXFIL-v1',
    'Data Exfiltration / Unusual Downloads',
    'Respond to potential data exfiltration or large data transfers',
    'alert',
    '{"min": "high"}'::jsonb,
    '["data_loss"]'::jsonb,
    'data-exfil-workflow',
    true,
    true,
    true
) ON CONFLICT DO NOTHING;

-- 10. Web Application Attack (WAF Alert)
INSERT INTO playbooks (
    id, tenant_id, key, name, description, target_type,
    severity_filter, category_filter, workflow_ref,
    requires_approval, is_enabled, is_builtin
)
VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000000',
    'WEB-WAF-ATTACK-v1',
    'Web Application Attack (WAF Alert)',
    'Respond to web attacks detected by WAF (SQL injection, XSS, etc.)',
    'alert',
    '{"min": "medium"}'::jsonb,
    '["web"]'::jsonb,
    'waf-attack-workflow',
    false,
    true,
    true
) ON CONFLICT DO NOTHING;

-- 11. Suspicious Use of Admin Tools / Remote Access
INSERT INTO playbooks (
    id, tenant_id, key, name, description, target_type,
    severity_filter, category_filter, workflow_ref,
    requires_approval, is_enabled, is_builtin
)
VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000000',
    'ADMIN-ABUSE-REMOTE-TOOLS-v1',
    'Suspicious Use of Admin Tools / Remote Access',
    'Investigate suspicious use of admin tools (RDP, PSExec, WinRM)',
    'alert',
    '{"min": "medium"}'::jsonb,
    '["privilege_abuse"]'::jsonb,
    'admin-abuse-workflow',
    true,
    true,
    true
) ON CONFLICT DO NOTHING;

-- 12. Lost / Stolen Device
INSERT INTO playbooks (
    id, tenant_id, key, name, description, target_type,
    severity_filter, category_filter, workflow_ref,
    requires_approval, is_enabled, is_builtin
)
VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000000',
    'DEVICE-LOST-STOLEN-v1',
    'Lost / Stolen Device (Laptop / Mobile)',
    'Respond to lost or stolen device: remote wipe, revoke access',
    'alert',
    '{"min": "high"}'::jsonb,
    '["device_security"]'::jsonb,
    'device-lost-workflow',
    true,
    true,
    true
) ON CONFLICT DO NOTHING;

-- AI Security Playbooks (3 additional)

-- 13. AI Prompt Injection Detection
INSERT INTO playbooks (
    id, tenant_id, key, name, description, target_type,
    severity_filter, category_filter, workflow_ref,
    requires_approval, is_enabled, is_builtin
)
VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000000',
    'AI-PROMPT-INJECTION-v1',
    'AI Prompt Injection / Jailbreak Attempt',
    'Respond to prompt injection or jailbreak attempts detected by AI Shield',
    'alert',
    '{"min": "medium"}'::jsonb,
    '["ai_security", "prompt_injection"]'::jsonb,
    'ai-prompt-injection-workflow',
    false,
    true,
    true
) ON CONFLICT DO NOTHING;

-- 14. AI Data Leakage (PII/Secrets)
INSERT INTO playbooks (
    id, tenant_id, key, name, description, target_type,
    severity_filter, category_filter, workflow_ref,
    requires_approval, is_enabled, is_builtin
)
VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000000',
    'AI-DATA-LEAKAGE-v1',
    'AI Data Leakage (PII/Secrets in Prompts)',
    'Investigate and prevent PII or secrets from being sent to LLMs',
    'alert',
    '{"min": "high"}'::jsonb,
    '["ai_security", "data_loss"]'::jsonb,
    'ai-data-leakage-workflow',
    true,
    true,
    true
) ON CONFLICT DO NOTHING;

-- 15. AI Policy Violation
INSERT INTO playbooks (
    id, tenant_id, key, name, description, target_type,
    severity_filter, category_filter, workflow_ref,
    requires_approval, is_enabled, is_builtin
)
VALUES (
    gen_random_uuid(),
    '00000000-0000-0000-0000-000000000000',
    'AI-POLICY-VIOLATION-v1',
    'AI Policy Violation / Unauthorized LLM Use',
    'Respond to unauthorized LLM usage or policy violations',
    'alert',
    '{"min": "medium"}'::jsonb,
    '["ai_security", "policy"]'::jsonb,
    'ai-policy-violation-workflow',
    false,
    true,
    true
) ON CONFLICT DO NOTHING;

-- Create indexes for efficient playbook queries
CREATE INDEX IF NOT EXISTS idx_playbooks_is_builtin ON playbooks(is_builtin) WHERE is_builtin = true;
CREATE INDEX IF NOT EXISTS idx_playbooks_key ON playbooks(key);
CREATE INDEX IF NOT EXISTS idx_playbooks_category_filter ON playbooks USING GIN(category_filter);

-- Comments
COMMENT ON COLUMN playbooks.is_builtin IS 'True for SentinelGrid built-in playbooks that cannot be deleted (but can be cloned)';
COMMENT ON COLUMN playbooks.key IS 'Unique identifier for built-in playbooks (e.g., PHISH-USER-REPORTED-v1)';

