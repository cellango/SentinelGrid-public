"""Focused auth-boundary coverage for SOAR tenant resolution and detection ingress."""

from pathlib import Path
import sys
from uuid import UUID

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

from app.api import detection_events
from app.core import security
from app.core.config import settings


TENANT_ID = UUID("00000000-0000-0000-0000-000000000111")
OTHER_TENANT_ID = UUID("00000000-0000-0000-0000-000000000222")
INTERNAL_TOKEN = "internal-test-token"


def _request(headers: dict[str, str] | None = None) -> Request:
    header_items = [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in (headers or {}).items()
    ]
    return Request({"type": "http", "headers": header_items})


def test_get_current_tenant_rejects_header_only_in_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    with pytest.raises(HTTPException) as exc:
        security.get_current_tenant(_request(), x_tenant_id=str(TENANT_ID))

    assert exc.value.status_code == 401
    assert "validated bearer token" in exc.value.detail


def test_get_current_tenant_rejects_forged_jwt(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    def fake_verify_token(_token: str):
        raise HTTPException(status_code=401, detail="Invalid token")

    monkeypatch.setattr(security, "verify_token_with_iam", fake_verify_token)

    with pytest.raises(HTTPException) as exc:
        security.get_current_tenant(
            _request({"Authorization": "Bearer forged.jwt.token"}),
            authorization="Bearer forged.jwt.token",
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token"


def test_get_current_tenant_rejects_mismatched_token_and_header_tenant(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    monkeypatch.setattr(
        security,
        "verify_token_with_iam",
        lambda _token: {"tenant_id": str(TENANT_ID), "user_id": "user-1"},
    )

    with pytest.raises(HTTPException) as exc:
        security.get_current_tenant(
            _request(
                {
                    "Authorization": "Bearer valid-user-token",
                    "X-Tenant-ID": str(OTHER_TENANT_ID),
                }
            ),
            authorization="Bearer valid-user-token",
            x_tenant_id=str(OTHER_TENANT_ID),
        )

    assert exc.value.status_code == 403
    assert "Tenant mismatch" in exc.value.detail


def test_get_current_tenant_accepts_internal_service_token_with_tenant_header(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "INTERNAL_SERVICE_TOKEN", INTERNAL_TOKEN)

    tenant_id = security.get_current_tenant(
        _request(
            {
                "Authorization": f"Bearer {INTERNAL_TOKEN}",
                "X-Tenant-ID": str(TENANT_ID),
            }
        ),
        authorization=f"Bearer {INTERNAL_TOKEN}",
        x_tenant_id=str(TENANT_ID),
    )

    assert tenant_id == TENANT_ID


@pytest.fixture
def detection_client(monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_SERVICE_TOKEN", INTERNAL_TOKEN)

    app = FastAPI()
    app.include_router(detection_events.router, prefix="/api/v1")

    class DummyIncidentCreator:
        def __init__(self, db):
            self.db = db

        async def create_incident_from_detection(self, detection_event, tenant_id):
            return {
                "incident_id": "inc-1",
                "playbook_execution_id": "exec-1",
                "tenant_id": tenant_id,
                "alert_type": detection_event["sg"]["alert_type"],
            }

    def override_session():
        yield object()

    monkeypatch.setattr(detection_events, "IncidentCreator", DummyIncidentCreator)
    app.dependency_overrides[detection_events.get_webhook_tenant_session] = override_session

    with TestClient(app) as client:
        yield client


def test_detection_event_ingest_requires_internal_token(detection_client):
    response = detection_client.post(
        "/api/v1/detection-events/ingest",
        headers={"X-Tenant-ID": str(TENANT_ID)},
        json={"sg": {"tenant_id": str(TENANT_ID), "alert_type": "phishing", "severity": "high"}},
    )

    assert response.status_code == 401
    assert "authorization" in response.json()["detail"].lower()


def test_detection_event_ingest_rejects_bad_tenant_header(detection_client):
    response = detection_client.post(
        "/api/v1/detection-events/ingest",
        headers={
            "Authorization": f"Bearer {INTERNAL_TOKEN}",
            "X-Tenant-ID": "not-a-uuid",
        },
        json={"sg": {"tenant_id": str(TENANT_ID), "alert_type": "phishing", "severity": "high"}},
    )

    assert response.status_code == 400
    assert "X-Tenant-ID" in response.json()["detail"]


def test_detection_event_ingest_rejects_mismatched_event_tenant(detection_client):
    response = detection_client.post(
        "/api/v1/detection-events/ingest",
        headers={
            "Authorization": f"Bearer {INTERNAL_TOKEN}",
            "X-Tenant-ID": str(TENANT_ID),
        },
        json={"sg": {"tenant_id": str(OTHER_TENANT_ID), "alert_type": "phishing", "severity": "high"}},
    )

    assert response.status_code == 400
    assert "Tenant ID mismatch" in response.json()["detail"]
