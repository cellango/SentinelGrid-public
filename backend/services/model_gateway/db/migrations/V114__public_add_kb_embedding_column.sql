-- Add embedding column to cybersecurity_knowledge_base for vector search
SET search_path = public;

CREATE EXTENSION IF NOT EXISTS "vector";

ALTER TABLE IF EXISTS cybersecurity_knowledge_base
    ADD COLUMN IF NOT EXISTS embedding vector(1024);
