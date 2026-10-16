import pytest
from datetime import datetime, timezone

from app.services.ingestion_service import IngestionService
from app.models.event import IngestBatchRequest, RawEvent


class DummyBatchProcessor:
    def __init__(self):
        self.calls = []

    async def add_event(self, tenant_id, ingest_event):
        self.calls.append((tenant_id, ingest_event))

    async def _flush_batch(self, tenant_id):
        self.calls.append(("flush", tenant_id))


@pytest.mark.asyncio
async def test_rejects_cross_tenant_event():
    svc = IngestionService()
    dummy_batch = DummyBatchProcessor()
    svc.batch_processor = dummy_batch

    request = IngestBatchRequest(
        events=[
            RawEvent(
                event_type="netflow",
                source="wazuh",
                timestamp=datetime.now(timezone.utc),
                tenant_id="tenant-b",
                raw_data={"message": "cross-tenant"},
            )
        ]
    )

    resp = await svc.ingest_batch(request, tenant_id="tenant-a")

    assert resp.ingested_count == 0
    assert resp.failed_count == 1
    assert "tenant_id mismatch" in " ".join(resp.errors)
    assert dummy_batch.calls == []


@pytest.mark.asyncio
async def test_batch_processor_scoped_per_tenant():
    svc = IngestionService()
    dummy_batch = DummyBatchProcessor()
    svc.batch_processor = dummy_batch

    request = IngestBatchRequest(
        events=[
            RawEvent(
                event_type="process",
                source="openedr",
                timestamp=datetime.now(timezone.utc),
                raw_data={"foo": "bar"},
            ),
            RawEvent(
                event_type="process",
                source="openedr",
                timestamp=datetime.now(timezone.utc),
                raw_data={"foo": "baz"},
            ),
        ]
    )

    resp = await svc.ingest_batch(request, tenant_id="tenant-123")

    assert resp.ingested_count == 2
    assert resp.failed_count == 0
    assert len(dummy_batch.calls) == 2
    for tenant_id_used, _ in dummy_batch.calls:
        assert tenant_id_used == "tenant-123"
