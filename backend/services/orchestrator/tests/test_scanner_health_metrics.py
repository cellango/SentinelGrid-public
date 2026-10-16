import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.api import scanner_health
from sg_core.service_metrics import get_service_metrics, reset_service_metrics


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise scanner_health.httpx.HTTPStatusError("boom", request=None, response=self)


class _FakeAsyncClient:
    def __init__(self, recorder, payload_by_url):
        self.recorder = recorder
        self.payload_by_url = payload_by_url

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def get(self, url, **kwargs):
        self.recorder.append(str(url))
        response = self.payload_by_url[str(url)]
        if isinstance(response, Exception):
            raise response
        return response


def _client():
    app = FastAPI()
    app.include_router(scanner_health.router, prefix="/api/v1/orchestrator")
    return TestClient(app)


def test_scanner_health_records_scan_pressure_metrics(monkeypatch):
    reset_service_metrics("orchestrator")
    calls = []
    monkeypatch.setattr(
        scanner_health.httpx,
        "AsyncClient",
        lambda *a, **k: _FakeAsyncClient(
            calls,
            {
                f"{scanner_health.REGISTRY_URL}/health": _FakeResponse(
                    {
                        "status": "ok",
                        "tenant_active": {"tenant-a": 2},
                        "scanner_active": {"trivy": 1, "zap": 2},
                        "metrics": {"queued": 3, "running": 2, "completed": 9, "failed": 1},
                    }
                )
            },
        ),
    )

    with _client() as client:
        response = client.get("/api/v1/orchestrator/scanner/health")

    assert response.status_code == 200
    snapshot = get_service_metrics("orchestrator").snapshot()
    assert snapshot["counters"]["scanner_health_requests_total"]["series"]["outcome=success"] == 1
    assert snapshot["gauges"]["scanner_orchestrator_up"]["__base__"] == 1
    assert snapshot["gauges"]["scanner_jobs_last"]["status=queued"] == 3
    assert snapshot["gauges"]["scanner_jobs_last"]["status=running"] == 2
    assert snapshot["gauges"]["scanner_tenant_active_total"]["__base__"] == 2
    assert snapshot["gauges"]["scanner_active_total"]["__base__"] == 3


def test_scanner_registry_records_enabled_and_disabled_counts(monkeypatch):
    reset_service_metrics("orchestrator")
    calls = []
    monkeypatch.setattr(
        scanner_health.httpx,
        "AsyncClient",
        lambda *a, **k: _FakeAsyncClient(
            calls,
            {
                f"{scanner_health.REGISTRY_URL}/scanners": _FakeResponse(
                    {
                        "items": [
                            {"id": "trivy", "enabled": True},
                            {"id": "zap", "enabled": None},
                            {"id": "semgrep", "enabled": False},
                        ]
                    }
                )
            },
        ),
    )

    with _client() as client:
        response = client.get("/api/v1/orchestrator/scanner/registry")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][1]["enabled"] is False
    snapshot = get_service_metrics("orchestrator").snapshot()
    assert snapshot["counters"]["scanner_registry_requests_total"]["series"]["outcome=success"] == 1
    assert snapshot["gauges"]["scanner_registry_items_total"]["__base__"] == 3
    assert snapshot["gauges"]["scanner_registry_enabled_total"]["__base__"] == 1
    assert snapshot["gauges"]["scanner_registry_disabled_total"]["__base__"] == 2
