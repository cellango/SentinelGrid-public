from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

from app.main import app
from app.api import framework as framework_api
from app.core.config import settings
from app.core.database import get_current_tenant, get_tenant_session


TENANT_ID = "00000000-0000-0000-0000-000000000111"


@pytest.fixture
def client():
    def override_get_current_tenant():
        return TENANT_ID

    def override_get_tenant_session():
        yield object()

    app.dependency_overrides[get_current_tenant] = override_get_current_tenant
    app.dependency_overrides[get_tenant_session] = override_get_tenant_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_map_to_frameworks_blocks_cross_tenant_request(client):
    response = client.post(
        "/api/v1/framework/map",
        json={
            "ticket_data": {"category": "phishing", "severity": "high"},
            "tenant_id": "00000000-0000-0000-0000-000000000222",
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Cross-tenant access denied"}


def test_map_to_frameworks_accepts_internal_service_tenant_header(monkeypatch):
    calls = {}

    def override_get_tenant_session():
        yield object()

    async def fake_map_incident(ticket_data):
        calls["ticket_data"] = ticket_data
        return {"nist_controls": [{"control_id": "IR-4"}], "soc2_criteria": []}

    app.dependency_overrides[get_tenant_session] = override_get_tenant_session
    monkeypatch.setattr(framework_api.framework_mapper, "map_incident", fake_map_incident)

    try:
        with TestClient(app) as test_client:
            response = test_client.post(
                "/api/v1/framework/map",
                headers={
                    "Authorization": f"Bearer {settings.INTERNAL_SERVICE_TOKEN}",
                    "X-Tenant-ID": TENANT_ID,
                },
                json={"category": "phishing", "severity": "high"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert calls["ticket_data"]["tenant_id"] == TENANT_ID


def test_map_to_frameworks_uses_authenticated_tenant(client, monkeypatch):
    async def fake_map_incident(ticket_data):
        assert ticket_data == {"category": "phishing", "severity": "high", "tenant_id": TENANT_ID}
        return {"nist_controls": [{"control_id": "IR-4"}], "soc2_criteria": []}

    monkeypatch.setattr(framework_api.framework_mapper, "map_incident", fake_map_incident)

    response = client.post(
        "/api/v1/framework/map",
        json={
            "ticket_data": {"category": "phishing", "severity": "high"},
            "tenant_id": TENANT_ID,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "nist_controls": [{"control_id": "IR-4"}],
        "soc2_criteria": [],
    }


def test_map_to_frameworks_accepts_direct_incident_shape(client, monkeypatch):
    async def fake_map_incident(ticket_data):
        assert ticket_data == {"category": "phishing", "severity": "high", "tenant_id": TENANT_ID}
        return {"nist_controls": [{"control_id": "IR-4"}], "soc2_criteria": []}

    monkeypatch.setattr(framework_api.framework_mapper, "map_incident", fake_map_incident)

    response = client.post(
        "/api/v1/framework/map",
        json={"category": "phishing", "severity": "high"},
    )

    assert response.status_code == 200
    assert response.json()["nist_controls"] == [{"control_id": "IR-4"}]


def test_map_nist_path_uses_authenticated_tenant(client, monkeypatch):
    calls = {}

    async def fake_map_incident_to_controls(ticket_data):
        calls["ticket_data"] = ticket_data
        return [{"control_id": "AC-2"}]

    monkeypatch.setattr(
        framework_api.framework_mapper.nist_mapper,
        "map_incident_to_controls",
        fake_map_incident_to_controls,
    )

    response = client.post(
        "/api/v1/framework/map/nist",
        json={"category": "suspicious_login", "severity": "high"},
    )

    assert response.status_code == 200
    assert response.json()["nist_controls"] == [{"control_id": "AC-2"}]
    assert calls["ticket_data"]["tenant_id"] == TENANT_ID


def test_map_to_nist_finding_path_returns_primary_control(client, monkeypatch):
    calls = {}

    async def fake_map_incident_to_controls(ticket_data):
        calls["ticket_data"] = ticket_data
        return [{"control_id": "IR-4"}, {"control_id": "AC-2"}]

    monkeypatch.setattr(
        framework_api.framework_mapper.nist_mapper,
        "map_incident_to_controls",
        fake_map_incident_to_controls,
    )

    response = client.post(
        "/api/v1/framework/map-to-nist",
        json={
            "finding_type": "iam",
            "finding_identifier": "missing_mfa",
            "severity": "high",
            "tenant_id": TENANT_ID,
        },
    )

    assert response.status_code == 200
    assert response.json()["nist_control_id"] == "IR-4"
    assert calls["ticket_data"]["tenant_id"] == TENANT_ID
    assert calls["ticket_data"]["category"] == "missing_mfa"


def test_map_to_soc2_finding_path_uses_authenticated_tenant(client, monkeypatch):
    calls = {}

    async def fake_map_incident_to_criteria(ticket_data):
        calls["ticket_data"] = ticket_data
        return [{"criterion_id": "CC6.1"}]

    monkeypatch.setattr(
        framework_api.framework_mapper.soc2_mapper,
        "map_incident_to_criteria",
        fake_map_incident_to_criteria,
    )

    response = client.post(
        "/api/v1/framework/map-to-soc2",
        json={"finding_type": "iam", "finding_identifier": "missing_mfa"},
    )

    assert response.status_code == 200
    assert response.json()["soc2_criteria"] == [{"criterion_id": "CC6.1"}]
    assert calls["ticket_data"]["tenant_id"] == TENANT_ID


def test_get_nist_control_works_with_tenant_scoped_dependencies(client):
    response = client.get("/api/v1/framework/nist/AC-2")

    assert response.status_code == 200
    assert response.json()["control_id"] == "AC-2"


def test_get_mitre_technique_works_with_tenant_scoped_dependencies(client):
    response = client.get("/api/v1/framework/mitre/T1078")

    assert response.status_code == 200
    assert response.json()["technique_id"] == "T1078"


def test_get_soc2_criterion_works_with_tenant_scoped_dependencies(client):
    response = client.get("/api/v1/framework/soc2/CC6.1")

    assert response.status_code == 200
    assert response.json()["criterion_id"] == "CC6.1"
