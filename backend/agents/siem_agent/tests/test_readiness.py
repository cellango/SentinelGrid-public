import asyncio
import json
import sys
import types

opensearchpy_module = types.ModuleType("opensearchpy")
opensearchpy_module.OpenSearch = object
opensearchpy_module.Search = object
opensearchpy_module.Q = object
opensearchpy_module.RequestsHttpConnection = object
opensearchpy_module.exceptions = types.SimpleNamespace(OpenSearchException=Exception, NotFoundError=Exception)
opensearchpy_exceptions_module = types.ModuleType("opensearchpy.exceptions")
opensearchpy_exceptions_module.OpenSearchException = Exception
opensearchpy_exceptions_module.NotFoundError = Exception
sys.modules.setdefault("opensearchpy", opensearchpy_module)
sys.modules.setdefault("opensearchpy.exceptions", opensearchpy_exceptions_module)

redis_stub = types.ModuleType("redis")


class _DummyRedisConnection:
    def ping(self):
        return True


def _from_url(*args, **kwargs):
    return _DummyRedisConnection()


redis_stub.from_url = _from_url
sys.modules.setdefault("redis", redis_stub)

import app.main as siem_main
from sg_core.service_health import build_dependency_status
from sg_core.service_metrics import reset_service_metrics


async def _healthy_db_probe(name: str, engine, *, critical: bool, **kwargs):
    return build_dependency_status(name, status="healthy", critical=critical, detail="query_ok")


async def _healthy_http_probe(name: str, url: str, *, critical: bool, **kwargs):
    return build_dependency_status(name, status="healthy", critical=critical, detail="ok", url=url)


async def _healthy_opensearch_probe():
    return build_dependency_status("opensearch", status="healthy", critical=True, detail="green")


def test_ready_returns_200_when_critical_dependencies_are_healthy(monkeypatch):
    reset_service_metrics("siem-agent")
    monkeypatch.setattr(siem_main, "probe_database_engine_async", _healthy_db_probe)
    monkeypatch.setattr(siem_main, "probe_http_dependency", _healthy_http_probe)
    monkeypatch.setattr(siem_main, "_probe_opensearch_dependency", _healthy_opensearch_probe)

    response = asyncio.run(siem_main.ready())
    metrics_payload = siem_main.metrics()
    payload = json.loads(response.body)

    assert response.status_code == 200
    assert payload["ready"] is True
    assert payload["status"] == "healthy"
    assert payload["dependencies"]["database"]["status"] == "healthy"
    assert payload["dependencies"]["opensearch"]["status"] == "healthy"
    assert payload["dependencies"]["iam_agent"]["status"] == "healthy"
    assert metrics_payload["counters"]["readiness_checks_total"]["series"]["outcome=ready"] == 1


def test_ready_returns_503_when_critical_dependency_is_down(monkeypatch):
    reset_service_metrics("siem-agent")

    async def _db_probe(name: str, engine, *, critical: bool, **kwargs):
        return build_dependency_status(name, status="unhealthy", critical=critical, detail="db_down")

    monkeypatch.setattr(siem_main, "probe_database_engine_async", _db_probe)
    monkeypatch.setattr(siem_main, "probe_http_dependency", _healthy_http_probe)
    monkeypatch.setattr(siem_main, "_probe_opensearch_dependency", _healthy_opensearch_probe)

    response = asyncio.run(siem_main.ready())
    payload = json.loads(response.body)

    assert response.status_code == 503
    assert payload["ready"] is False
    assert payload["status"] == "unhealthy"
    assert payload["dependencies"]["database"]["status"] == "unhealthy"


def test_metrics_prometheus_endpoint_returns_prometheus_text(monkeypatch):
    reset_service_metrics("siem-agent")
    monkeypatch.setattr(siem_main, "probe_database_engine_async", _healthy_db_probe)
    monkeypatch.setattr(siem_main, "probe_http_dependency", _healthy_http_probe)
    monkeypatch.setattr(siem_main, "_probe_opensearch_dependency", _healthy_opensearch_probe)

    response = asyncio.run(siem_main.ready())
    metrics_response = siem_main.metrics_prometheus()

    assert response.status_code == 200
    assert metrics_response.status_code == 200
    assert metrics_response.headers["content-type"].startswith("text/plain")
    assert 'readiness_checks_total{outcome="ready",service="siem-agent"} 1.0' in metrics_response.body.decode()
