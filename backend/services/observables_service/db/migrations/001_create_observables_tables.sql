-- Migration: Create observables and observable_analyzers tables
-- Version: 001
-- Description: Tables for tracking and enriching observables via Cortex

-- Create observables table
CREATE TABLE IF NOT EXISTS observables (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    observable_type VARCHAR(50) NOT NULL,
    value TEXT NOT NULL,
    source_event_id UUID,
    first_seen TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMP NOT NULL DEFAULT NOW(),
    tlp_level INTEGER DEFAULT 2 CHECK (tlp_level BETWEEN 0 AND 3),
    enrichment_status VARCHAR(20) DEFAULT 'pending',
    enrichment_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT unique_tenant_observable UNIQUE (tenant_id, observable_type, value)
);

-- Create indexes for observables
CREATE INDEX IF NOT EXISTS idx_observables_tenant ON observables(tenant_id);
CREATE INDEX IF NOT EXISTS idx_observables_type ON observables(observable_type);
CREATE INDEX IF NOT EXISTS idx_observables_status ON observables(enrichment_status);
CREATE INDEX IF NOT EXISTS idx_observables_tenant_type_value ON observables(tenant_id, observable_type, value);
CREATE INDEX IF NOT EXISTS idx_observables_source_event ON observables(source_event_id) WHERE source_event_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_observables_created_at ON observables(created_at DESC);

-- Create observable_analyzers table
CREATE TABLE IF NOT EXISTS observable_analyzers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    observable_id UUID NOT NULL REFERENCES observables(id) ON DELETE CASCADE,
    analyzer_id VARCHAR(100) NOT NULL,
    cortex_job_id VARCHAR(100),
    status VARCHAR(20) DEFAULT 'pending',
    report JSONB,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    CONSTRAINT fk_observable FOREIGN KEY (observable_id) REFERENCES observables(id) ON DELETE CASCADE
);

-- Create indexes for observable_analyzers
CREATE INDEX IF NOT EXISTS idx_analyzers_observable ON observable_analyzers(observable_id);
CREATE INDEX IF NOT EXISTS idx_analyzers_cortex_job ON observable_analyzers(cortex_job_id) WHERE cortex_job_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_analyzers_status ON observable_analyzers(status);

-- Add comments
COMMENT ON TABLE observables IS 'Observables extracted from events and enriched via Cortex';
COMMENT ON TABLE observable_analyzers IS 'Cortex analyzer jobs run on observables';
COMMENT ON COLUMN observables.tlp_level IS 'Traffic Light Protocol: 0=WHITE, 1=GREEN, 2=AMBER, 3=RED';
COMMENT ON COLUMN observables.enrichment_status IS 'Status: pending, enriching, completed, failed, skipped';

