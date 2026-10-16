import asyncio
import json

import app.main as model_gateway_main
from sg_core.service_health import build_dependency_status
from sg_core.service_metrics import reset_service_metrics


async def _healthy_db_probe(name: str, engine, *, critical: bool, **kwargs):
    return build_dependency_status(name, status="healthy", critical=critical, detail="query_ok")


def test_ready_returns_200_when_database_is_healthy(monkeypatch):
    reset_service_metrics("model-gateway")
    monkeypatch.setattr(model_gateway_main, "probe_database_engine_async", _healthy_db_probe)
    monkeypatch.setattr(
        model_gateway_main,
        "_probe_path_dependency",
        lambda name, path_value, *, critical, writable=False: build_dependency_status(
            name,
            status="healthy",
            critical=critical,
            detail="path_ok",
            extra={"path": path_value},
        ),
    )

    response = asyncio.run(model_gateway_main.ready())
    metrics_payload = model_gateway_main.metrics()
    payload = json.loads(response.body)

    assert response.status_code == 200
    assert payload["ready"] is True
    assert payload["status"] == "healthy"
    assert payload["dependencies"]["database"]["status"] == "healthy"
    assert metrics_payload["counters"]["readiness_checks_total"]["series"]["outcome=ready"] == 1


def test_ready_stays_green_when_only_storage_paths_are_degraded(monkeypatch):
    reset_service_metrics("model-gateway")
    monkeypatch.setattr(model_gateway_main, "probe_database_engine_async", _healthy_db_probe)

    def _probe(name, path_value, *, critical, writable=False):
        return build_dependency_status(
            name,
            status="unhealthy",
            critical=critical,
            detail="path_missing",
            extra={"path": path_value},
        )

    monkeypatch.setattr(model_gateway_main, "_probe_path_dependency", _probe)

    response = asyncio.run(model_gateway_main.ready())
    payload = json.loads(response.body)

    assert response.status_code == 200
    assert payload["ready"] is True
    assert payload["status"] == "degraded"
    assert payload["dependencies"]["base_model_storage"]["critical"] is False
    assert payload["dependencies"]["adapter_storage"]["critical"] is False


def test_metrics_prometheus_endpoint_returns_prometheus_text(monkeypatch):
    reset_service_metrics("model-gateway")
    monkeypatch.setattr(model_gateway_main, "probe_database_engine_async", _healthy_db_probe)
    monkeypatch.setattr(
        model_gateway_main,
        "_probe_path_dependency",
        lambda name, path_value, *, critical, writable=False: build_dependency_status(
            name,
            status="healthy",
            critical=critical,
            detail="path_ok",
            extra={"path": path_value},
        ),
    )

    response = asyncio.run(model_gateway_main.ready())
    metrics_response = model_gateway_main.metrics_prometheus()

    assert response.status_code == 200
    assert metrics_response.status_code == 200
    assert metrics_response.headers["content-type"].startswith("text/plain")
    assert 'readiness_checks_total{outcome="ready",service="model-gateway"} 1.0' in metrics_response.body.decode()
