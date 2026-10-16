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
async def test_tenant_mismatch_rejected(monkeypatch):
    service = IngestionService()
    dummy_batch = DummyBatchProcessor()
    service.batch_processor = dummy_batch

    request = IngestBatchRequest(
        events=[
            RawEvent(
                event_type="process",
                source="openedr",
                timestamp=datetime.now(timezone.utc),
                tenant_id="tenant-b",
                raw_data={"foo": "bar"},
            )
        ]
    )

    response = await service.ingest_batch(request, tenant_id="tenant-a")

    assert response.ingested_count == 0
    assert response.failed_count == 1
    assert dummy_batch.calls == []
    assert any("tenant_id mismatch" in err for err in response.errors)


@pytest.mark.asyncio
async def test_tenant_defaults_to_auth_context(monkeypatch):
    service = IngestionService()
    dummy_batch = DummyBatchProcessor()
    service.batch_processor = dummy_batch

    request = IngestBatchRequest(
        events=[
            RawEvent(
                event_type="netflow",
                source="wazuh",
                timestamp=datetime.now(timezone.utc),
                raw_data={"message": "ok"},
            )
        ]
    )

    response = await service.ingest_batch(request, tenant_id="tenant-a")

    assert response.ingested_count == 1
    assert response.failed_count == 0
    assert len(dummy_batch.calls) == 1
    tenant_id_used, ingest_event = dummy_batch.calls[0]
    assert tenant_id_used == "tenant-a"
    assert ingest_event.ecs_fields.tenant_id == "tenant-a"


@pytest.mark.asyncio
async def test_edr_source_and_sidecar_propagate(monkeypatch):
    service = IngestionService()
    dummy_batch = DummyBatchProcessor()
    service.batch_processor = dummy_batch

    request = IngestBatchRequest(
        events=[
            RawEvent(
                event_type="process",
                source="OpenEDR",
                timestamp=datetime.now(timezone.utc),
                raw_data={"foo": "bar"},
                edr_source="openedr",
                sidecar_enabled=True,
            )
        ]
    )

    response = await service.ingest_batch(request, tenant_id="tenant-x")

    assert response.ingested_count == 1
    assert response.failed_count == 0
    assert len(dummy_batch.calls) == 1
    _, ingest_event = dummy_batch.calls[0]
    assert ingest_event.ecs_fields.edr_source == "sentinelguard-openedr"
    assert ingest_event.ecs_fields.sidecar_enabled is True
