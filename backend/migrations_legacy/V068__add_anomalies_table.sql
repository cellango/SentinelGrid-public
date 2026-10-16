-- Migration: Add Anomalies Table
-- Description: Stores detected security anomalies and their status
-- Date: 2025-01-28

CREATE TABLE IF NOT EXISTS anomalies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID,
    anomaly_type VARCHAR(100) NOT NULL, -- 'impossible_travel', 'unusual_location', 'unusual_device', 'failed_logins', 'mfa_fatigue'
    severity VARCHAR(50) NOT NULL, -- 'low', 'medium', 'high', 'critical'
    title VARCHAR(255) NOT NULL,
    description TEXT,
    risk_score FLOAT DEFAULT 0.0, -- 0-100
    metadata JSONB, -- Additional anomaly details
    status VARCHAR(50) DEFAULT 'open', -- 'open', 'acknowledged', 'resolved', 'false_positive'
    acknowledged_at TIMESTAMP,
    acknowledged_by UUID,
    resolved_at TIMESTAMP,
    resolved_by UUID,
    resolution_notes TEXT,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_anomalies_tenant ON anomalies(tenant_id);
CREATE INDEX IF NOT EXISTS idx_anomalies_user ON anomalies(user_id);
CREATE INDEX IF NOT EXISTS idx_anomalies_type ON anomalies(anomaly_type);
CREATE INDEX IF NOT EXISTS idx_anomalies_severity ON anomalies(severity);
CREATE INDEX IF NOT EXISTS idx_anomalies_status ON anomalies(status);
CREATE INDEX IF NOT EXISTS idx_anomalies_detected_at ON anomalies(detected_at);

-- Create table for automated responses
CREATE TABLE IF NOT EXISTS automated_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    anomaly_id UUID REFERENCES anomalies(id) ON DELETE CASCADE,
    response_type VARCHAR(100) NOT NULL, -- 'lock_account', 'force_mfa', 'send_alert', 'revoke_session'
    action_taken VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'executed', 'failed'
    executed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for automated responses
CREATE INDEX IF NOT EXISTS idx_automated_responses_tenant ON automated_responses(tenant_id);
CREATE INDEX IF NOT EXISTS idx_automated_responses_anomaly ON automated_responses(anomaly_id);
CREATE INDEX IF NOT EXISTS idx_automated_responses_status ON automated_responses(status);

-- Add comments
COMMENT ON TABLE anomalies IS 'Detected security anomalies and threats';
COMMENT ON TABLE automated_responses IS 'Automated responses to security anomalies';
