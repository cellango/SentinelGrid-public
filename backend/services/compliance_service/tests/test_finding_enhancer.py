from pathlib import Path
import os
import sys
from uuid import UUID

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

os.environ.setdefault("DB_HOST", "localhost")

from app.services import finding_enhancer as enhancer_module
from app.services.finding_enhancer import FindingEnhancer


TENANT_ID = UUID("00000000-0000-0000-0000-000000000111")


class FakeResponse:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return self._payload


class FakeAsyncClient:
    calls = []
    response_payload = {}

    def __init__(self, timeout):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url, json, headers):
        self.calls.append({"url": url, "json": json, "headers": headers})
        return FakeResponse(self.response_payload)


@pytest.fixture(autouse=True)
def fake_http_client(monkeypatch):
    FakeAsyncClient.calls = []
    monkeypatch.setattr(enhancer_module.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(enhancer_module.settings, "FRAMEWORK_SERVICE_URL", "http://framework-service")
    monkeypatch.setattr(enhancer_module.settings, "INTERNAL_SERVICE_TOKEN", "internal-token")


@pytest.mark.asyncio
async def test_map_to_nist_control_sends_real_tenant_context():
    FakeAsyncClient.response_payload = {"nist_control_id": "IR-4"}

    control_id = await FindingEnhancer(db=object())._map_to_nist_control("missing_mfa", "iam", TENANT_ID)

    assert control_id == "IR-4"
    call = FakeAsyncClient.calls[0]
    assert call["url"] == "http://framework-service/api/v1/framework/map-to-nist"
    assert call["json"] == {
        "finding_type": "iam",
        "finding_identifier": "missing_mfa",
        "tenant_id": str(TENANT_ID),
    }
    assert call["headers"]["Authorization"] == "Bearer internal-token"
    assert call["headers"]["X-Tenant-ID"] == str(TENANT_ID)
    assert "00000000-0000-0000-0000-000000000000" not in str(call["json"])


@pytest.mark.asyncio
async def test_map_to_soc2_criteria_sends_real_tenant_context():
    FakeAsyncClient.response_payload = {"soc2_criteria": [{"criterion_id": "CC6.1"}]}

    criteria = await FindingEnhancer(db=object())._map_to_soc2_criteria("missing_mfa", "iam", TENANT_ID)

    assert criteria == [{"criterion_id": "CC6.1"}]
    call = FakeAsyncClient.calls[0]
    assert call["url"] == "http://framework-service/api/v1/framework/map-to-soc2"
    assert call["json"] == {
        "finding_type": "iam",
        "finding_identifier": "missing_mfa",
        "severity": "medium",
        "tenant_id": str(TENANT_ID),
    }
    assert call["headers"]["Authorization"] == "Bearer internal-token"
    assert call["headers"]["X-Tenant-ID"] == str(TENANT_ID)
    assert "00000000-0000-0000-0000-000000000000" not in str(call["json"])

