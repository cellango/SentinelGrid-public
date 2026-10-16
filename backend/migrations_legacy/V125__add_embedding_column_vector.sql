-- Align security_event_embeddings with pgvector and MiniLM model (384 dims)
CREATE EXTENSION IF NOT EXISTS "vector";

-- Replace the embedding column to ensure correct dimension and avoid legacy mismatches.
ALTER TABLE IF EXISTS security_event_embeddings
    DROP COLUMN IF EXISTS embedding;

ALTER TABLE IF EXISTS security_event_embeddings
    ADD COLUMN IF NOT EXISTS embedding vector(384);
