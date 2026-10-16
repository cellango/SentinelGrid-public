-- Schema-only migration: durable evidence idempotency keys.

ALTER TABLE public.evidence_items
    ADD COLUMN IF NOT EXISTS idempotency_key character varying(255);

ALTER TABLE public.evidence_collection_tasks
    ADD COLUMN IF NOT EXISTS idempotency_key character varying(255);

CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_items_tenant_idempotency
    ON public.evidence_items USING btree (tenant_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL AND deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_tasks_tenant_idempotency
    ON public.evidence_collection_tasks USING btree (tenant_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL AND deleted_at IS NULL;

COMMENT ON COLUMN public.evidence_items.idempotency_key IS
    'Tenant-scoped deterministic key used to avoid duplicate durable evidence writes from retrying collectors.';

COMMENT ON COLUMN public.evidence_collection_tasks.idempotency_key IS
    'Tenant-scoped deterministic key used to avoid duplicate evidence collection task writes.';
