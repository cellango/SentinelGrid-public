-- Migration: Add support for Out-of-the-Box (OOTB) playbooks
-- This migration adds fields to support built-in playbooks with NIST phases, triggers, and framework mappings

ALTER TABLE playbooks ADD COLUMN IF NOT EXISTS playbook_key VARCHAR(255);
ALTER TABLE playbooks ADD COLUMN IF NOT EXISTS is_builtin BOOLEAN DEFAULT false;
ALTER TABLE playbooks ADD COLUMN IF NOT EXISTS severity_default VARCHAR(50); -- 'low', 'medium', 'high', 'critical'
ALTER TABLE playbooks ADD COLUMN IF NOT EXISTS applicable_sources TEXT[] DEFAULT ARRAY[]::TEXT[];
ALTER TABLE playbooks ADD COLUMN IF NOT EXISTS triggers TEXT[] DEFAULT ARRAY[]::TEXT[];
ALTER TABLE playbooks ADD COLUMN IF NOT EXISTS prerequisites TEXT[] DEFAULT ARRAY[]::TEXT[];
ALTER TABLE playbooks ADD COLUMN IF NOT EXISTS artifacts_required TEXT[] DEFAULT ARRAY[]::TEXT[];
ALTER TABLE playbooks ADD COLUMN IF NOT EXISTS phases JSONB; -- NIST IR phases structure
ALTER TABLE playbooks ADD COLUMN IF NOT EXISTS cis_controls TEXT[] DEFAULT ARRAY[]::TEXT[]; -- CIS Controls

-- Add index for built-in playbooks
CREATE INDEX IF NOT EXISTS idx_playbooks_is_builtin ON playbooks(is_builtin);
CREATE INDEX IF NOT EXISTS idx_playbooks_playbook_key ON playbooks(playbook_key);

-- Add unique constraint for built-in playbooks (only one version per key)
CREATE UNIQUE INDEX IF NOT EXISTS idx_playbooks_builtin_key_unique 
ON playbooks(playbook_key) 
WHERE is_builtin = true;

-- Comments
COMMENT ON COLUMN playbooks.playbook_key IS 'Unique identifier for built-in playbooks (e.g., PHISH-USER-REPORTED-v1)';
COMMENT ON COLUMN playbooks.is_builtin IS 'True if this is a SentinelGrid built-in playbook that cannot be deleted';
COMMENT ON COLUMN playbooks.severity_default IS 'Default severity level for incidents handled by this playbook';
COMMENT ON COLUMN playbooks.applicable_sources IS 'List of data sources this playbook applies to (e.g., email, siem, edr)';
COMMENT ON COLUMN playbooks.triggers IS 'List of trigger conditions that activate this playbook';
COMMENT ON COLUMN playbooks.prerequisites IS 'List of prerequisites required to use this playbook';
COMMENT ON COLUMN playbooks.artifacts_required IS 'List of artifacts required for this playbook';
COMMENT ON COLUMN playbooks.phases IS 'NIST IR phases structure with steps (Detection & Analysis, Containment, etc.)';
COMMENT ON COLUMN playbooks.cis_controls IS 'CIS Controls mapped to this playbook';

