import asyncio
import json

import app.main as ingestion_main
from sg_core.service_health import build_dependency_status
from sg_core.service_metrics import reset_service_metrics


class DummyBatchProcessor:
    def queue_summary(self):
        return {
            "pending_events": 2,
            "tenants_with_pending_batches": 1,
            "active_batch_timers": 1,
            "max_batch_depth": 2,
        }


async def _healthy_probe(name: str, url: str, *, critical: bool, **kwargs):
    return build_dependency_status(name, status="healthy", critical=critical, detail="ok", url=url)


def test_ready_returns_200_when_critical_dependencies_are_healthy(monkeypatch):
    reset_service_metrics("ingestion-service")
    monkeypatch.setattr(ingestion_main, "probe_http_dependency", _healthy_probe)
    monkeypatch.setattr(ingestion_main, "get_batch_processor", lambda: DummyBatchProcessor())
    monkeypatch.setattr(ingestion_main.settings, "ENABLE_EMBEDDINGS", False, raising=False)

    # Direct probe unit calls; HTTP /ready still requires an owned operational contract.
    response = asyncio.run(ingestion_main.readiness())
    metrics_payload = ingestion_main.metrics()

    assert response.status_code == 200
    payload = json.loads(response.body)
    assert payload["ready"] is True
    assert payload["status"] == "healthy"
    assert payload["dependencies"]["iam_agent"]["status"] == "healthy"
    assert payload["dependencies"]["opensearch"]["status"] == "healthy"
    assert payload["queue"]["pending_events"] == 2
    assert metrics_payload["counters"]["readiness_checks_total"]["series"]["outcome=ready"] == 1


def test_ready_stays_green_when_only_model_gateway_is_down(monkeypatch):
    reset_service_metrics("ingestion-service")

    async def _probe(name: str, url: str, *, critical: bool, **kwargs):
        status = "unhealthy" if name == "model_gateway" else "healthy"
        detail = "down" if status == "unhealthy" else "ok"
        return build_dependency_status(name, status=status, critical=critical, detail=detail, url=url)

    monkeypatch.setattr(ingestion_main, "probe_http_dependency", _probe)
    monkeypatch.setattr(ingestion_main, "get_batch_processor", lambda: DummyBatchProcessor())
    monkeypatch.setattr(ingestion_main.settings, "ENABLE_EMBEDDINGS", True, raising=False)

    response = asyncio.run(ingestion_main.readiness())

    assert response.status_code == 200
    payload = json.loads(response.body)
    assert payload["ready"] is True
    assert payload["status"] == "degraded"
    assert payload["dependencies"]["model_gateway"]["critical"] is False
    assert payload["dependencies"]["model_gateway"]["status"] == "unhealthy"
    assert payload["embeddings_enabled"] is True
