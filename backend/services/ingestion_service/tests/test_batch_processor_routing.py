from datetime import datetime, timezone

from app.services.batch_processor import BatchProcessor
from app.models.event import IngestEvent, ECSField


def make_event(source_name: str, tenant_id: str, raw_source: str = None) -> IngestEvent:
    return IngestEvent(
        ecs_fields=ECSField(
            timestamp=datetime.now(timezone.utc),
            tenant_id=tenant_id,
            event_type="test",
            source={"name": source_name, "type": "endpoint"},
        ),
        raw_data={"source": raw_source or source_name},
    )


def test_cloudtrail_routes_to_cloudtrail_pipeline():
    bp = BatchProcessor()
    ev = make_event("aws_cloudtrail", "tenant-a")

    index, pipeline = bp._resolve_index_pipeline("tenant-a", ev)

    assert index == "tenant-a-cloudtrail"
    assert pipeline == "pipeline-cloudtrail"


def test_unknown_or_edr_sources_route_to_logs_with_tenant_prefix():
    bp = BatchProcessor()
    ev = make_event("openedr", "tenant-a")

    index, pipeline = bp._resolve_index_pipeline("tenant-a", ev)

    assert index == "tenant-a-logs"
    assert pipeline is None


def test_different_tenants_get_isolated_indices():
    bp = BatchProcessor()
    ev = make_event("openedr", "tenant-a")
    ev2 = make_event("openedr", "tenant-b")

    index_a, _ = bp._resolve_index_pipeline("tenant-a", ev)
    index_b, _ = bp._resolve_index_pipeline("tenant-b", ev2)

    assert index_a != index_b
    assert index_a == "tenant-a-logs"
    assert index_b == "tenant-b-logs"
