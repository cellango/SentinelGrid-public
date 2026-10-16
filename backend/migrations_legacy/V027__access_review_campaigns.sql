-- Migration: Access Review (Attestation) Campaigns
-- Date: 2025-12-02
-- Purpose: Quarterly access reviews for SOC 2 CC6.x compliance

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Access review campaigns
CREATE TABLE IF NOT EXISTS access_review_campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    campaign_type VARCHAR(50) NOT NULL, -- 'admin_review', 'app_access_review', 'role_review', 'all_access_review'
    scope JSONB, -- Which users/roles/apps to review
    status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'active', 'completed', 'cancelled'
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(tenant_id, realm_name, name)
);

CREATE INDEX idx_access_review_campaigns_tenant_realm ON access_review_campaigns(tenant_id, realm_name);
CREATE INDEX idx_access_review_campaigns_status ON access_review_campaigns(status);
CREATE INDEX idx_access_review_campaigns_type ON access_review_campaigns(campaign_type);
CREATE INDEX idx_access_review_campaigns_dates ON access_review_campaigns(start_date, end_date);

-- Individual review items
CREATE TABLE IF NOT EXISTS access_review_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES access_review_campaigns(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL,
    
    -- Reviewer information
    reviewer_user_id TEXT NOT NULL, -- Who must review
    reviewer_email VARCHAR(255),
    reviewer_name VARCHAR(255),
    
    -- Subject information
    subject_user_id TEXT NOT NULL, -- User being reviewed
    subject_email VARCHAR(255),
    subject_name VARCHAR(255),
    
    -- Access being reviewed
    entitlement_id UUID REFERENCES entitlements(id),
    app_id UUID REFERENCES apps(id),
    access_type VARCHAR(100), -- 'role', 'entitlement', 'group', 'permission'
    access_name VARCHAR(255),
    access_description TEXT,
    
    -- Review decision
    decision VARCHAR(50) DEFAULT 'pending', -- 'pending', 'approved', 'revoked', 'escalated'
    justification TEXT,
    reviewed_at TIMESTAMPTZ,
    
    -- Metadata
    metadata JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_access_review_items_campaign ON access_review_items(campaign_id);
CREATE INDEX idx_access_review_items_tenant_realm ON access_review_items(tenant_id, realm_name);
CREATE INDEX idx_access_review_items_reviewer ON access_review_items(reviewer_user_id);
CREATE INDEX idx_access_review_items_subject ON access_review_items(subject_user_id);
CREATE INDEX idx_access_review_items_decision ON access_review_items(decision);
CREATE INDEX idx_access_review_items_entitlement ON access_review_items(entitlement_id);

-- Review decisions audit (for compliance trail)
CREATE TABLE IF NOT EXISTS access_review_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    review_item_id UUID NOT NULL REFERENCES access_review_items(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL,
    
    -- Decision details
    reviewer_user_id TEXT NOT NULL,
    reviewer_email VARCHAR(255),
    decision VARCHAR(50) NOT NULL, -- 'approved', 'revoked', 'escalated'
    justification TEXT NOT NULL,
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    
    decided_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_access_review_decisions_item ON access_review_decisions(review_item_id);
CREATE INDEX idx_access_review_decisions_tenant_realm ON access_review_decisions(tenant_id, realm_name);
CREATE INDEX idx_access_review_decisions_reviewer ON access_review_decisions(reviewer_user_id);
CREATE INDEX idx_access_review_decisions_at ON access_review_decisions(decided_at DESC);

-- Campaign statistics (for reporting)
CREATE TABLE IF NOT EXISTS access_review_statistics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES access_review_campaigns(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    realm_name VARCHAR(255) NOT NULL,
    
    -- Statistics
    total_items INTEGER DEFAULT 0,
    items_reviewed INTEGER DEFAULT 0,
    items_approved INTEGER DEFAULT 0,
    items_revoked INTEGER DEFAULT 0,
    items_escalated INTEGER DEFAULT 0,
    items_pending INTEGER DEFAULT 0,
    
    -- Timing
    average_review_time_seconds INTEGER,
    
    -- Compliance metrics
    completion_percentage NUMERIC(5,2),
    on_time_completion BOOLEAN,
    
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(campaign_id)
);

CREATE INDEX idx_access_review_stats_tenant_realm ON access_review_statistics(tenant_id, realm_name);
CREATE INDEX idx_access_review_stats_campaign ON access_review_statistics(campaign_id);

-- Comments for documentation
COMMENT ON TABLE access_review_campaigns IS 'Access review campaigns for SOC 2 CC6.x compliance';
COMMENT ON COLUMN access_review_campaigns.campaign_type IS 'Type: admin_review, app_access_review, role_review, all_access_review';
COMMENT ON COLUMN access_review_campaigns.scope IS 'JSON defining which users/roles/apps to include in review';
COMMENT ON TABLE access_review_items IS 'Individual access items to be reviewed in campaigns';
COMMENT ON COLUMN access_review_items.decision IS 'Review decision: pending, approved, revoked, escalated';
COMMENT ON TABLE access_review_decisions IS 'Audit trail of review decisions for compliance';
COMMENT ON TABLE access_review_statistics IS 'Campaign completion statistics for reporting';

