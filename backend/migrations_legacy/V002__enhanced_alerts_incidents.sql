-- Migration 002: Enhanced Alerts and Incidents with NIST/MITRE Framework Support
-- Date: 2025-01-28
-- Description: Add NIST/MITRE framework fields and vulnerability associations to alerts and incidents

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Add NIST/MITRE fields to alerts table
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS nist_controls JSONB;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS mitre_tactics JSONB;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS mitre_techniques JSONB;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS cve_ids TEXT[];
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS exploit_indicators JSONB;

-- Add NIST/MITRE fields to incidents table
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS nist_controls JSONB;
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS mitre_tactics JSONB;
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS mitre_techniques JSONB;
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS cve_ids TEXT[];
ALTER TABLE incidents ADD COLUMN IF NOT EXISTS exploit_indicators JSONB;

-- Add indexes for framework fields (for faster lookups)
CREATE INDEX IF NOT EXISTS idx_alerts_nist_controls ON alerts USING GIN (nist_controls);
CREATE INDEX IF NOT EXISTS idx_alerts_mitre_tactics ON alerts USING GIN (mitre_tactics);
CREATE INDEX IF NOT EXISTS idx_alerts_mitre_techniques ON alerts USING GIN (mitre_techniques);
CREATE INDEX IF NOT EXISTS idx_alerts_cve_ids ON alerts USING GIN (cve_ids);
CREATE INDEX IF NOT EXISTS idx_incidents_nist_controls ON incidents USING GIN (nist_controls);
CREATE INDEX IF NOT EXISTS idx_incidents_mitre_tactics ON incidents USING GIN (mitre_tactics);
CREATE INDEX IF NOT EXISTS idx_incidents_mitre_techniques ON incidents USING GIN (mitre_techniques);
CREATE INDEX IF NOT EXISTS idx_incidents_cve_ids ON incidents USING GIN (cve_ids);

-- Comments for documentation
COMMENT ON COLUMN alerts.nist_controls IS 'Array of NIST SP 800-53 control mappings: [{"control_id": "IR-4", "title": "Incident Response Planning", "relevance": "..."}]';
COMMENT ON COLUMN alerts.mitre_tactics IS 'Array of MITRE ATT&CK tactic mappings: [{"tactic_id": "TA0001", "name": "Initial Access", ...}]';
COMMENT ON COLUMN alerts.mitre_techniques IS 'Array of MITRE ATT&CK technique mappings: [{"technique_id": "T1078", "name": "Valid Accounts", ...}]';
COMMENT ON COLUMN alerts.cve_ids IS 'Array of CVE IDs associated with this alert: ["CVE-2024-1234", "CVE-2024-5678"]';
COMMENT ON COLUMN alerts.exploit_indicators IS 'Indicators that this alert exploits a vulnerability: {"exploit_type": "...", "indicators": [...]}';

COMMENT ON COLUMN incidents.nist_controls IS 'Array of NIST SP 800-53 control mappings';
COMMENT ON COLUMN incidents.mitre_tactics IS 'Array of MITRE ATT&CK tactic mappings';
COMMENT ON COLUMN incidents.mitre_techniques IS 'Array of MITRE ATT&CK technique mappings';
COMMENT ON COLUMN incidents.cve_ids IS 'Array of CVE IDs associated with this incident';
COMMENT ON COLUMN incidents.exploit_indicators IS 'Indicators that this incident exploits a vulnerability';

