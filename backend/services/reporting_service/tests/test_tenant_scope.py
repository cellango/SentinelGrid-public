import os
import sys
import pytest
import asyncio

# Ensure libs are on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..", ".."))
LIBS = os.path.join(ROOT, "backend", "libs")
sys.path.insert(0, LIBS)

from app.services.report_generator import ReportGeneratorService
from app.core.config import settings


class FakeResponse:
    def __init__(self, json_data):
        self._json = json_data

    def json(self):
        return self._json

    def raise_for_status(self):
        return None


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self.last_request = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def get(self, url, headers=None, params=None):
        self.last_request = {"url": url, "headers": headers or {}, "params": params or {}}
        return FakeResponse({"ok": True})


def test_fetch_section_uses_compliance_service(monkeypatch):
    service = ReportGeneratorService()

    fake_client = FakeAsyncClient()
    monkeypatch.setattr("app.services.report_generator.httpx.AsyncClient", lambda *a, **k: fake_client)

    data = asyncio.run(
        service._fetch_section_data(
            {"data_source": "/api/v1/compliance/soc2/coverage"},
            tenant_id="tenant-123",
            date_range=None,
        )
    )

    assert fake_client.last_request is not None
    assert fake_client.last_request["url"] == f"{settings.COMPLIANCE_SERVICE_URL}/compliance/soc2/coverage"
    headers = fake_client.last_request["headers"]
    assert headers.get("X-Tenant-ID") == "tenant-123"
    assert headers.get("Authorization", "").startswith("Bearer")
    assert data.get("ok") is True
