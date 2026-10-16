-- Align KB embeddings to 384 dimensions for MiniLM
SET search_path = public;

CREATE EXTENSION IF NOT EXISTS "vector";

ALTER TABLE IF EXISTS cybersecurity_knowledge_base
    DROP COLUMN IF EXISTS embedding;

ALTER TABLE IF EXISTS cybersecurity_knowledge_base
    ADD COLUMN embedding vector(384);
