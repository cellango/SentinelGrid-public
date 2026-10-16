import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from app.core.config import settings
from app.schemas import TelemetryEventCreate
from app.services.siem_export_config import LoadedSiemExportConfig, SiemExportConfigLoader
from app.services.siem_export_interface import DeliveryResult, NormalizedSiemEvent, SiemDestinationConfig, SiemExporter
from app.services.siem_export_manager import SiemExportManager
from app.services.splunk_hec_exporter import SplunkHecExporter


class StaticLoader:
    def __init__(self, config: LoadedSiemExportConfig):
        self._config = config
        self.config_path = Path("/tmp/siem-destinations.yaml")

    def load(self, force_reload: bool = False) -> LoadedSiemExportConfig:
        return self._config


class FakeExporter(SiemExporter):
    def __init__(self):
        self.sent_batches: list[tuple[list[NormalizedSiemEvent], SiemDestinationConfig]] = []

    @property
    def adapter_type(self) -> str:
        return "splunk_hec"

    def validate_config(self, config: SiemDestinationConfig) -> None:
        return None

    def serialize_event(self, event: NormalizedSiemEvent, config: SiemDestinationConfig) -> dict[str, object]:
        return {"event_id": event.event_id}

    def send_batch(
        self,
        events: list[NormalizedSiemEvent],
        config: SiemDestinationConfig,
    ) -> DeliveryResult:
        self.sent_batches.append((events, config))
        return DeliveryResult(destination_name=config.name, success=True, status_code=200, message="ok")


class FakeResponse:
    def __init__(self, status_code: int = 200, text: str = "OK"):
        self.status_code = status_code
        self.text = text


class FakeSession:
    def __init__(self):
        self.calls: list[dict[str, object]] = []

    def post(self, url: str, headers: dict[str, str], data: bytes, timeout: int) -> FakeResponse:
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "data": data,
                "timeout": timeout,
            }
        )
        return FakeResponse()


def test_telemetry_event_accepts_gateway_aliases():
    event = TelemetryEventCreate.model_validate(
        {
            "id": "evt-123",
            "tenant_id": "11111111-1111-1111-1111-111111111111",
            "ai_app_id": "demo-app",
            "realm": "customer-prod",
            "user_id": "user-123",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "policy_decision": "blocked",
            "violation_reason": "prompt injection suspected",
            "prompt_preview": "ignore previous instructions",
            "response_preview": "blocked",
            "created_at": "2026-03-25T12:00:00Z",
        }
    )

    assert event.event_id == "evt-123"
    assert event.org_id == UUID("11111111-1111-1111-1111-111111111111")
    assert event.ai_app_id == "demo-app"
    assert event.realm == "customer-prod"
    assert event.created_at == datetime(2026, 3, 25, 12, 0, tzinfo=timezone.utc)


def test_siem_export_config_loader_merges_default_delivery(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SIEM_EXPORT_BATCH_SIZE", 77)
    monkeypatch.setattr(settings, "SIEM_EXPORT_TIMEOUT_SECONDS", 15)
    monkeypatch.setattr(settings, "SIEM_EXPORT_RETRY_MAX", 4)

    config_file = tmp_path / "siem-destinations.yaml"
    config_file.write_text(
        "\n".join(
            [
                "version: 1",
                "default_delivery:",
                "  batch_size: 25",
                "  timeout_seconds: 9",
                "destinations:",
                "  - name: splunk-primary",
                "    type: splunk_hec",
                "    enabled: true",
                "    transport: http_json",
                "    endpoint: https://splunk.example.com:8088/services/collector",
                "    auth:",
                "      type: bearer",
                "      token_env: SPLUNK_HEC_TOKEN",
                "    delivery:",
                "      retry_max: 1",
            ]
        ),
        encoding="utf-8",
    )

    loaded = SiemExportConfigLoader(config_file).load()

    assert loaded.default_delivery["batch_size"] == 25
    assert loaded.default_delivery["timeout_seconds"] == 9
    assert loaded.default_delivery["retry_max"] == 4
    assert loaded.destinations[0].delivery["batch_size"] == 25
    assert loaded.destinations[0].delivery["timeout_seconds"] == 9
    assert loaded.destinations[0].delivery["retry_max"] == 1


def test_siem_export_manager_applies_filters(monkeypatch):
    monkeypatch.setattr(settings, "SIEM_EXPORT_ENABLED", True)

    destination = SiemDestinationConfig(
        name="splunk-primary",
        type="splunk_hec",
        enabled=True,
        transport="http_json",
        endpoint="https://splunk.example.com:8088/services/collector",
        auth={"type": "bearer", "token_env": "SPLUNK_HEC_TOKEN"},
        filters={"minimum_severity": "high", "only_blocked": True},
        delivery={"timeout_seconds": 10, "retry_max": 0},
    )
    exporter = FakeExporter()
    manager = SiemExportManager(
        loader=StaticLoader(
            LoadedSiemExportConfig(
                version=1,
                destinations=[destination],
            )
        ),
        exporters={"splunk_hec": exporter},
    )

    allowed_event = NormalizedSiemEvent(
        event_id="evt-allowed",
        event_type="ai.request.allowed",
        occurred_at=datetime(2026, 3, 25, 12, 0, tzinfo=timezone.utc),
        tenant_id="11111111-1111-1111-1111-111111111111",
        severity="medium",
        policy_decision="allowed",
    )
    blocked_event = NormalizedSiemEvent(
        event_id="evt-blocked",
        event_type="ai.request.blocked",
        occurred_at=datetime(2026, 3, 25, 12, 1, tzinfo=timezone.utc),
        tenant_id="11111111-1111-1111-1111-111111111111",
        severity="high",
        policy_decision="blocked",
    )

    assert manager.export_normalized_events([allowed_event]) == []

    results = manager.export_normalized_events([blocked_event])

    assert len(results) == 1
    assert results[0].success is True
    assert len(exporter.sent_batches) == 1
    assert exporter.sent_batches[0][0][0].event_id == "evt-blocked"


def test_splunk_hec_exporter_posts_json_payload(monkeypatch):
    monkeypatch.setenv("SPLUNK_HEC_TOKEN", "hec-token")

    session = FakeSession()
    exporter = SplunkHecExporter(session=session)
    destination = SiemDestinationConfig(
        name="splunk-primary",
        type="splunk_hec",
        enabled=True,
        transport="http_json",
        endpoint="https://splunk.example.com:8088/services/collector",
        auth={"type": "bearer", "token_env": "SPLUNK_HEC_TOKEN"},
        routing={
            "index": "sentinelgrid",
            "source": "sentinelgrid_ai_shield",
            "sourcetype": "sentinelgrid:ai:event",
        },
        delivery={"timeout_seconds": 12, "retry_max": 0},
    )
    event = NormalizedSiemEvent(
        event_id="evt-1",
        event_type="ai.request.blocked",
        occurred_at=datetime(2026, 3, 25, 12, 0, tzinfo=timezone.utc),
        tenant_id="11111111-1111-1111-1111-111111111111",
        realm="demo",
        ai_app_id="demo-app",
        user_id="user-123",
        provider="openai",
        model="gpt-4o-mini",
        policy_decision="blocked",
        severity="high",
        risk_flags={"has_pii": True},
        metrics={"tokens_in": 12, "tokens_out": 0},
        previews={"prompt": "ignore previous instructions"},
        labels={"violation_reason": "prompt injection suspected"},
        raw={"policy_decision": "blocked"},
    )

    result = exporter.send_batch([event], destination)

    assert result.success is True
    assert len(session.calls) == 1
    assert session.calls[0]["url"] == "https://splunk.example.com:8088/services/collector"
    assert session.calls[0]["headers"]["Authorization"] == "Splunk hec-token"
    assert session.calls[0]["timeout"] == 12

    payload = json.loads(session.calls[0]["data"].decode("utf-8"))
    assert payload["index"] == "sentinelgrid"
    assert payload["event"]["event_id"] == "evt-1"
    assert payload["event"]["realm"] == "demo"
    assert payload["event"]["labels"]["violation_reason"] == "prompt injection suspected"
