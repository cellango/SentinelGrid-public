-- Migration: Certificate Service Schema
-- Creates tables for CA authorities, certificates, and certificate requests

-- CA Authorities table
CREATE TABLE IF NOT EXISTS ca_authorities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL, -- 'step-ca', 'aws-acm-pca', etc.
    config JSONB NOT NULL, -- URLs, ARNs, credentials, etc.
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- 'active', 'disabled'
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ca_authorities_name ON ca_authorities(name);
CREATE INDEX IF NOT EXISTS idx_ca_authorities_type ON ca_authorities(type);
CREATE INDEX IF NOT EXISTS idx_ca_authorities_status ON ca_authorities(status);

-- Certificates table
CREATE TABLE IF NOT EXISTS certificates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    serial_number VARCHAR(255) NOT NULL UNIQUE,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE, -- NULL for service certs
    subject_cn VARCHAR(255) NOT NULL,
    dns_names TEXT[] DEFAULT ARRAY[]::TEXT[],
    ip_addresses INET[] DEFAULT ARRAY[]::INET[],
    spki_fingerprint VARCHAR(255), -- SHA-256 fingerprint of public key
    usage VARCHAR(50) NOT NULL, -- 'service', 'agent'
    service_type VARCHAR(100), -- 'siem-agent', 'iam-agent', 'orchestrator', etc.
    agent_id VARCHAR(255), -- For agent certificates
    ca_authority_id UUID NOT NULL REFERENCES ca_authorities(id),
    issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    revocation_reason VARCHAR(100), -- 'unspecified', 'key_compromise', 'superseded', etc.
    status VARCHAR(50) NOT NULL DEFAULT 'issued', -- 'issued', 'revoked', 'expired'
    metadata JSONB, -- Additional metadata (CSR info, etc.)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_certificates_serial_number ON certificates(serial_number);
CREATE INDEX IF NOT EXISTS idx_certificates_tenant_id ON certificates(tenant_id);
CREATE INDEX IF NOT EXISTS idx_certificates_subject_cn ON certificates(subject_cn);
CREATE INDEX IF NOT EXISTS idx_certificates_status ON certificates(status);
CREATE INDEX IF NOT EXISTS idx_certificates_expires_at ON certificates(expires_at);
CREATE INDEX IF NOT EXISTS idx_certificates_usage ON certificates(usage);
CREATE INDEX IF NOT EXISTS idx_certificates_service_type ON certificates(service_type);
CREATE INDEX IF NOT EXISTS idx_certificates_agent_id ON certificates(agent_id);
CREATE INDEX IF NOT EXISTS idx_certificates_ca_authority_id ON certificates(ca_authority_id);

-- Certificate Requests table (for audit and tracking)
CREATE TABLE IF NOT EXISTS certificate_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    certificate_id UUID REFERENCES certificates(id) ON DELETE SET NULL,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    requestor_type VARCHAR(50) NOT NULL, -- 'service', 'agent', 'admin'
    requestor_id VARCHAR(255), -- Service name, agent ID, or user ID
    csr_pem TEXT, -- Certificate Signing Request (optional, for audit)
    dns_names TEXT[] DEFAULT ARRAY[]::TEXT[],
    ip_addresses INET[] DEFAULT ARRAY[]::INET[],
    ttl_hours INTEGER, -- Requested TTL
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'rejected', 'issued'
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_certificate_requests_certificate_id ON certificate_requests(certificate_id);
CREATE INDEX IF NOT EXISTS idx_certificate_requests_tenant_id ON certificate_requests(tenant_id);
CREATE INDEX IF NOT EXISTS idx_certificate_requests_status ON certificate_requests(status);
CREATE INDEX IF NOT EXISTS idx_certificate_requests_requestor ON certificate_requests(requestor_type, requestor_id);

-- Agent Bootstrap Tokens table (for one-time agent enrollment)
CREATE TABLE IF NOT EXISTS agent_bootstrap_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE, -- SHA-256 hash of token
    agent_id VARCHAR(255), -- Optional: pre-assigned agent ID
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ, -- When token was used for enrollment
    created_by UUID, -- User ID who created the token
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_bootstrap_tokens_tenant_id ON agent_bootstrap_tokens(tenant_id);
CREATE INDEX IF NOT EXISTS idx_agent_bootstrap_tokens_token_hash ON agent_bootstrap_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_agent_bootstrap_tokens_expires_at ON agent_bootstrap_tokens(expires_at);

-- Comments
COMMENT ON TABLE ca_authorities IS 'Certificate Authority backends (step-ca, AWS ACM Private CA, etc.)';
COMMENT ON TABLE certificates IS 'Issued X.509 certificates with metadata';
COMMENT ON TABLE certificate_requests IS 'Certificate enrollment requests for audit and tracking';
COMMENT ON TABLE agent_bootstrap_tokens IS 'One-time tokens for agent certificate enrollment';

