import pytest
from datetime import datetime, timezone

from app.services.normalizer import ECSNormalizer
from app.models.event import RawEvent


def test_edr_source_detection_and_fields():
    normalizer = ECSNormalizer()
    raw_event = RawEvent(
        event_type="process",
        source="OpenEDR",
        timestamp=datetime.now(timezone.utc),
        raw_data={
            "process_id": 1234,
            "parent_pid": 12,
            "process_name": "cmd.exe",
            "command_line": "cmd.exe /c whoami",
            "file_path": r"C:\\Windows\\System32\\cmd.exe",
            "sensor_status": "healthy",
            "hunt_id": "hunt-1",
            "task_id": "task-1",
            "collection_id": "col-1",
            "edr_source": "openEDR",
        },
    )

    ecs = normalizer.normalize(raw_event, "tenant-1")

    assert ecs.tenant_id == "tenant-1"
    assert ecs.edr_source == "sentinelguard-openedr"
    # Default sidecar_enabled when edr_source is present
    assert ecs.sidecar_enabled is True
    assert ecs.process["pid"] == 1234
    assert ecs.process["ppid"] == 12
    assert ecs.process["command_line"].startswith("cmd.exe")
    assert ecs.file["path"].endswith("cmd.exe")
    assert ecs.sensor["status"] == "healthy"
    assert ecs.hunt["id"] == "hunt-1"
    assert ecs.task["id"] == "task-1"
    assert ecs.collection["id"] == "col-1"


def test_edr_source_from_metadata_and_sidecar_override_false():
    normalizer = ECSNormalizer()
    raw_event = RawEvent(
        event_type="process",
        source="endpoint-agent",
        timestamp=datetime.now(timezone.utc),
        metadata={"edr_source": "velociraptor"},
        sidecar_enabled=False,
        raw_data={
            "process_id": 42,
            "edr_source": None,  # ensure metadata wins
        },
    )

    ecs = normalizer.normalize(raw_event, "tenant-x")

    assert ecs.edr_source == "sentinelguard-velociraptor"
    assert ecs.sidecar_enabled is False
    assert ecs.process["pid"] == 42
