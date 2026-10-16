import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app.main as orchestrator_main
from app.services.metrics import metrics_tracker
from sg_core.service_health import build_dependency_status
from sg_core.service_metrics import reset_service_metrics


async def _healthy_http_probe(name: str, url: str, *, critical: bool, **kwargs):
    return build_dependency_status(name, status="healthy", critical=critical, detail="ok", url=url)


async def _healthy_db_probe(name: str, engine, *, critical: bool, **kwargs):
    return build_dependency_status(name, status="healthy", critical=critical, detail="query_ok")


def test_ready_returns_200_when_critical_dependencies_are_healthy(monkeypatch):
    reset_service_metrics("orchestrator")
    monkeypatch.setattr(orchestrator_main, "probe_http_dependency", _healthy_http_probe)
    monkeypatch.setattr(orchestrator_main, "probe_database_engine_async", _healthy_db_probe)

    with TestClient(orchestrator_main.app) as client:
        response = client.get("/ready")
        metrics_response = client.get("/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is True
    assert payload["status"] == "healthy"
    assert payload["dependencies"]["database"]["status"] == "healthy"
    assert payload["dependencies"]["iam_agent"]["status"] == "healthy"
    metrics_payload = metrics_response.json()
    assert metrics_payload["runtime"]["counters"]["readiness_checks_total"]["series"]["outcome=ready"] == 1


def test_ready_stays_green_when_only_noncritical_dependency_is_down(monkeypatch):
    reset_service_metrics("orchestrator")
    async def _http_probe(name: str, url: str, *, critical: bool, **kwargs):
        status = "unhealthy" if name == "siem_agent" else "healthy"
        detail = "down" if status == "unhealthy" else "ok"
        return build_dependency_status(name, status=status, critical=critical, detail=detail, url=url)

    monkeypatch.setattr(orchestrator_main, "probe_http_dependency", _http_probe)
    monkeypatch.setattr(orchestrator_main, "probe_database_engine_async", _healthy_db_probe)

    with TestClient(orchestrator_main.app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is True
    assert payload["status"] == "degraded"
    assert payload["dependencies"]["siem_agent"]["critical"] is False
    assert payload["dependencies"]["siem_agent"]["status"] == "unhealthy"


def test_metrics_prometheus_endpoint_includes_runtime_and_operation_series(monkeypatch):
    reset_service_metrics("orchestrator")
    metrics_tracker.reset()
    metrics_tracker.mark_queued("scan")
    monkeypatch.setattr(orchestrator_main, "probe_http_dependency", _healthy_http_probe)
    monkeypatch.setattr(orchestrator_main, "probe_database_engine_async", _healthy_db_probe)

    with TestClient(orchestrator_main.app) as client:
        ready_response = client.get("/ready")
        metrics_response = client.get("/metrics/prometheus")

    assert ready_response.status_code == 200
    assert metrics_response.status_code == 200
    assert metrics_response.headers["content-type"].startswith("text/plain")
    assert 'readiness_checks_total{outcome="ready",service="orchestrator"} 1.0' in metrics_response.text
    assert 'orchestrator_operation_queued_by_type{service="orchestrator",operation_type="scan"} 1' in metrics_response.text
