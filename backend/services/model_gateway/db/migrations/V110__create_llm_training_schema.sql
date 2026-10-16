-- Moved from V1.0 to avoid version conflicts with core migrations
CREATE SCHEMA IF NOT EXISTS llm_training;

CREATE TABLE IF NOT EXISTS llm_training.runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    status TEXT NOT NULL,
    model_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
