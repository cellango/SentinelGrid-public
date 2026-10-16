-- Migration: Create leads table for incomplete signups
-- Date: 2025-01-29
-- Purpose: Store signup information before payment completion (treat as leads, not accounts)

CREATE TABLE IF NOT EXISTS leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    company_name VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    password_hash VARCHAR(255), -- Hashed password, will be used when creating account
    user_count INTEGER NOT NULL, -- User count from signup (1-25, 26-50, etc.)
    user_band VARCHAR(20), -- Calculated band: '1-25', '26-50', '51-100', '101-250', '250+'
    compliance_required BOOLEAN DEFAULT FALSE,
    package_name VARCHAR(50), -- 'protect' or 'protect_comply'
    estimated_price_cents INTEGER, -- Price shown to user
    stripe_session_id VARCHAR(255), -- Stripe checkout session ID if payment started
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'payment_started', 'converted', 'expired'
    metadata JSONB, -- Additional data (billing period, etc.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE, -- When to cleanup if not converted
    converted_at TIMESTAMP WITH TIME ZONE, -- When account was created
    converted_to_tenant_id UUID, -- Reference to tenant if converted
    converted_to_customer_id UUID -- Reference to customer if converted
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_stripe_session ON leads(stripe_session_id);
CREATE INDEX IF NOT EXISTS idx_leads_expires_at ON leads(expires_at);

-- Comments
COMMENT ON TABLE leads IS 'Stores incomplete signups as leads before account creation';
COMMENT ON COLUMN leads.status IS 'pending: just created, payment_started: checkout initiated, converted: account created, expired: cleanup candidate';
COMMENT ON COLUMN leads.expires_at IS 'Leads expire after 30 days if not converted';
COMMENT ON COLUMN leads.password_hash IS 'Hashed password stored securely, used when creating account after payment';

