-- Migration: Mark knowledge base data load point (renumbered from V1.1 to avoid conflicts)
-- This migration creates a marker table to track data loads
-- Actual data loading with embeddings is done by Python script (load_knowledge_base_data.py)

-- Create data migration tracking table
CREATE TABLE IF NOT EXISTS data_migration_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    migration_version VARCHAR(20) NOT NULL UNIQUE,
    migration_name TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed'
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    records_loaded INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Insert marker for knowledge base data load
INSERT INTO data_migration_history (migration_version, migration_name, status)
VALUES ('1.1', 'Knowledge base data load marker', 'pending')
ON CONFLICT (migration_version) DO NOTHING;
