import asyncio
from datetime import datetime, timezone

import pytest

import app.services.batch_processor as batch_processor_module
from app.models.event import ECSField, IngestEvent
from app.services.batch_processor import BatchProcessor
from sg_core.service_metrics import get_service_metrics, reset_service_metrics


def make_event(tenant_id: str, *, severity: str | None = None, event_kind: str | None = None) -> IngestEvent:
    return IngestEvent(
        ecs_fields=ECSField(
            timestamp=datetime.now(timezone.utc),
            tenant_id=tenant_id,
            event_type="test",
            source={"name": "openedr", "type": "endpoint"},
            event={"kind": event_kind} if event_kind else None,
        ),
        raw_data={
            "source": "openedr",
            "message": "Suspicious activity detected",
            **({"severity": severity} if severity else {}),
        },
    )


@pytest.mark.asyncio
async def test_batch_processor_records_queue_pressure_and_flush_metrics(monkeypatch):
    reset_service_metrics("ingestion-service")
    bp = BatchProcessor()
    bp.enable_embeddings = False
    bp.batch_size = 10
    bp.batch_timeout = 60

    async def noop_send(tenant_id, events):
        return None

    monkeypatch.setattr(bp, "_send_to_opensearch", noop_send)

    await bp.add_event("tenant-a", make_event("tenant-a"))

    metrics = get_service_metrics("ingestion-service").snapshot()
    assert bp.queue_summary() == {
        "pending_events": 1,
        "tenants_with_pending_batches": 1,
        "active_batch_timers": 1,
        "max_batch_depth": 1,
    }
    assert metrics["counters"]["ingestion_events_total"]["series"]["outcome=accepted"] == 1
    assert metrics["gauges"]["ingestion_pending_events"]["__base__"] == 1.0
    assert metrics["gauges"]["ingestion_pending_tenants"]["__base__"] == 1.0

    await bp._flush_batch("tenant-a", trigger="manual")

    metrics = get_service_metrics("ingestion-service").snapshot()
    assert metrics["counters"]["ingestion_batch_flushes_total"]["series"][
        "outcome=success,trigger=manual"
    ] == 1
    assert metrics["gauges"]["ingestion_pending_events"]["__base__"] == 0.0
    assert metrics["gauges"]["ingestion_active_batch_timers"]["__base__"] == 0.0


@pytest.mark.asyncio
async def test_batch_processor_records_embedding_failure_pressure(monkeypatch):
    reset_service_metrics("ingestion-service")
    bp = BatchProcessor()
    bp.enable_embeddings = True

    class FailingAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            raise RuntimeError("model gateway down")

    original_create_task = batch_processor_module.asyncio.create_task
    scheduled_tasks = []

    def schedule_and_track(coro):
        task = original_create_task(coro)
        scheduled_tasks.append(task)
        return task

    monkeypatch.setattr(batch_processor_module.httpx, "AsyncClient", lambda *a, **k: FailingAsyncClient())
    monkeypatch.setattr(batch_processor_module.asyncio, "create_task", schedule_and_track)

    await bp._maybe_send_embeddings("tenant-a", [make_event("tenant-a", severity="high", event_kind="alert")])
    await asyncio.gather(*scheduled_tasks)

    metrics = get_service_metrics("ingestion-service").snapshot()
    assert bp.embedding_summary() == {
        "tenants_with_activity": 1,
        "attempted_total": 1,
        "success_total": 0,
        "failed_total": 1,
        "cap_used_total": 1,
        "cap_limit_per_tenant": bp.embeddings_cap,
    }
    assert metrics["counters"]["ingestion_embedding_summaries_total"]["series"]["outcome=attempted"] == 1
    assert metrics["counters"]["ingestion_embedding_summaries_total"]["series"]["outcome=failed"] == 1
    assert metrics["gauges"]["ingestion_embeddings_cap_used_total"]["__base__"] == 1.0
    assert metrics["gauges"]["ingestion_embeddings_activity_tenants"]["__base__"] == 1.0
