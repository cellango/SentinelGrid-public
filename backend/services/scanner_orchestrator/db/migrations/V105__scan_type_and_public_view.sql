-- Add scan_type column, normalize scanner_id -> scan_type via lookup, and expose a public view without scanner_id.

-- 1) scan_categories lookup
CREATE TABLE IF NOT EXISTS scan_categories (
    scanner_id TEXT PRIMARY KEY,
    scan_type TEXT NOT NULL,
    display_label TEXT,
    icon TEXT,
    color TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Seed common mappings (idempotent)
INSERT INTO scan_categories (scanner_id, scan_type, display_label)
VALUES
    ('cloud', 'cloud', 'Cloud posture'),
    ('prowler', 'cloud', 'Cloud posture'),
    ('trivy', 'vuln', 'Container/host vuln'),
    ('git', 'git', 'Git / repo scan'),
    ('semgrep', 'sast', 'App SAST'),
    ('appsec-sast', 'sast', 'App SAST'),
    ('gitleaks', 'secrets', 'Secrets scan'),
    ('git-secrets', 'secrets', 'Secrets scan'),
    ('checkov', 'iac', 'IaC posture'),
    ('iac-checks', 'iac', 'IaC posture'),
    ('zap', 'dast', 'DAST'),
    ('endpoint', 'endpoint', 'Endpoint / EDR')
ON CONFLICT (scanner_id) DO NOTHING;

-- 2) scan_type column on scans
ALTER TABLE scans ADD COLUMN IF NOT EXISTS scan_type TEXT;

-- 3) Backfill scan_type using the lookup or fallback to scanner_id
UPDATE scans s
SET scan_type = COALESCE(sc.scan_type, s.scan_type, s.scanner_id)
FROM scan_categories sc
WHERE s.scan_type IS NULL AND s.scanner_id = sc.scanner_id;

-- For any remaining NULLs, set a safe fallback
UPDATE scans SET scan_type = COALESCE(scan_type, scanner_id, 'other') WHERE scan_type IS NULL;

-- 4) Public view without scanner_id; prefer normalized scan_type
DROP VIEW IF EXISTS scans_public;
CREATE VIEW scans_public AS
SELECT
    s.id,
    s.tenant_id,
    s.scan_type,
    s.target_ref,
    s.status,
    s.summary,
    s.created_at,
    s.updated_at,
    s.started_at,
    s.finished_at,
    s.raw_artifact_url
FROM scans s;
