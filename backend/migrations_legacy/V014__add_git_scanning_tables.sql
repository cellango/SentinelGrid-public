-- Migration: Git Security Scanning Tables
-- Created: 2025-11-30
-- Description: Adds tables for Git security scanning jobs and tracking

-- ============================================================================
-- Git Security Scans
-- ============================================================================
CREATE TABLE IF NOT EXISTS git_security_scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    repo_id UUID NOT NULL REFERENCES git_repositories(id) ON DELETE CASCADE,
    scan_types JSONB NOT NULL, -- Array of scan types: ["secrets", "dependencies", "code"]
    branch VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'queued', -- queued, running, completed, failed
    findings_count INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_git_security_scans_customer_id ON git_security_scans(customer_id);
CREATE INDEX idx_git_security_scans_repo_id ON git_security_scans(repo_id);
CREATE INDEX idx_git_security_scans_status ON git_security_scans(status);
CREATE INDEX idx_git_security_scans_created_at ON git_security_scans(created_at);

COMMENT ON TABLE git_security_scans IS 'Tracks Git repository security scan jobs';
COMMENT ON COLUMN git_security_scans.scan_types IS 'JSON array of scan types: ["secrets", "dependencies", "code"]';

-- ============================================================================
-- Update triggers
-- ============================================================================
CREATE TRIGGER update_git_security_scans_updated_at BEFORE UPDATE ON git_security_scans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

