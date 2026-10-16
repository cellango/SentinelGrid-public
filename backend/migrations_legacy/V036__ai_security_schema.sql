-- SentinelGridAIShield Database Schema
-- AI Security tables for apps, policies, and events

-- AI Applications table
CREATE TABLE IF NOT EXISTS ai_apps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    environment VARCHAR(50) NOT NULL CHECK (environment IN ('dev', 'staging', 'prod')),
    description TEXT,
    allowed_models TEXT[],
    allow_external_providers BOOLEAN DEFAULT true,
    max_context_tokens INTEGER DEFAULT 100000,
    api_key_hash VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(org_id, name, environment)
);

CREATE INDEX idx_ai_apps_org ON ai_apps(org_id);
CREATE INDEX idx_ai_apps_created ON ai_apps(created_at DESC);

-- AI Policies table
CREATE TABLE IF NOT EXISTS ai_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    ai_app_id UUID REFERENCES ai_apps(id) ON DELETE CASCADE,  -- NULL = org-wide default
    block_pii_outbound BOOLEAN DEFAULT false,
    block_secrets_outbound BOOLEAN DEFAULT true,
    block_external_llms BOOLEAN DEFAULT false,
    block_jailbreak_patterns BOOLEAN DEFAULT true,
    require_approval_for_high_risk_tools BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(org_id, ai_app_id)  -- One policy per org or per app
);

CREATE INDEX idx_ai_policies_org ON ai_policies(org_id);
CREATE INDEX idx_ai_policies_app ON ai_policies(ai_app_id);

-- AI Events table (summary storage, full events in OpenSearch)
CREATE TABLE IF NOT EXISTS ai_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL,
    ai_app_id UUID REFERENCES ai_apps(id) ON DELETE SET NULL,
    user_id VARCHAR(255),
    provider VARCHAR(100),
    model VARCHAR(255),
    has_pii BOOLEAN DEFAULT false,
    has_secrets BOOLEAN DEFAULT false,
    prompt_injection_suspected BOOLEAN DEFAULT false,
    policy_decision VARCHAR(50) CHECK (policy_decision IN ('allowed', 'blocked', 'modified')),
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_ai_events_org_created ON ai_events(org_id, created_at DESC);
CREATE INDEX idx_ai_events_app_created ON ai_events(ai_app_id, created_at DESC);
CREATE INDEX idx_ai_events_policy_decision ON ai_events(policy_decision);
CREATE INDEX idx_ai_events_has_pii ON ai_events(has_pii) WHERE has_pii = true;
CREATE INDEX idx_ai_events_has_secrets ON ai_events(has_secrets) WHERE has_secrets = true;
CREATE INDEX idx_ai_events_injection ON ai_events(prompt_injection_suspected) WHERE prompt_injection_suspected = true;

-- Comments
COMMENT ON TABLE ai_apps IS 'Registered AI applications using SentinelGridAIShield';
COMMENT ON TABLE ai_policies IS 'Security policies for AI applications';
COMMENT ON TABLE ai_events IS 'Summary of AI events (full data in OpenSearch sg-ai-events-*)';
COMMENT ON COLUMN ai_policies.ai_app_id IS 'NULL means this is the org-wide default policy';

