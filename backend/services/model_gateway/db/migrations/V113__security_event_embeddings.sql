-- Security Event Embeddings table for pgvector storage (renumbered from V1.4)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

CREATE TABLE IF NOT EXISTS security_event_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL,
    source TEXT NOT NULL,
    agent_id TEXT,
    host_id TEXT,
    os_id_ref TEXT NOT NULL,
    "timestamp" TIMESTAMPTZ NOT NULL,
    summary TEXT NOT NULL,
    fields JSONB,
    embedding vector(1024),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_security_event_embeddings_unique
    ON security_event_embeddings(tenant_id, source, os_id_ref);
