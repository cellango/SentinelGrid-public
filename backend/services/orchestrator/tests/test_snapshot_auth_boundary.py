from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

from app.api import snapshot
from app.core.config import settings


TENANT_ID = UUID("00000000-0000-0000-0000-000000000111")
OTHER_TENANT_ID = UUID("00000000-0000-0000-0000-000000000222")
INTERNAL_TOKEN = "internal-test-token"


class DummySnapshotService:
    async def generate_security_snapshot(self, tenant_id: str):
        return {
            "tenant_id": tenant_id,
            "generated_at": "2026-04-18T00:00:00Z",
            "summary": {
                "events_count": 0,
                "alerts_count": 0,
                "users_active": 0,
                "users_total": 0,
            },
            "alerts_by_severity": {},
            "alerts_by_status": {},
            "top_findings": [],
            "iam_summary": {
                "users_count": 0,
                "active_users_count": 0,
                "roles_count": 0,
                "groups_count": 0,
            },
            "ai_analysis": {
                "posture": "Good",
                "risk_level": "Low",
                "key_findings": [],
                "recommendations": [],
                "summary": "No elevated risk signals detected.",
            },
        }


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_SERVICE_TOKEN", INTERNAL_TOKEN)

    app = FastAPI()
    app.include_router(snapshot.router)
    app.dependency_overrides[snapshot.get_snapshot_service] = DummySnapshotService

    with TestClient(app) as test_client:
        yield test_client


def test_security_snapshot_accepts_internal_service_token_with_matching_tenant(client):
    response = client.get(
        f"/tenant/{TENANT_ID}/security-snapshot",
        headers={
            "Authorization": f"Bearer {INTERNAL_TOKEN}",
            "X-Tenant-ID": str(TENANT_ID),
        },
    )

    assert response.status_code == 200
    assert response.json()["tenant_id"] == str(TENANT_ID)


def test_security_snapshot_rejects_internal_service_token_with_mismatched_tenant(client):
    response = client.get(
        f"/tenant/{TENANT_ID}/security-snapshot",
        headers={
            "Authorization": f"Bearer {INTERNAL_TOKEN}",
            "X-Tenant-ID": str(OTHER_TENANT_ID),
        },
    )

    assert response.status_code == 403
    assert "Tenant mismatch" in response.json()["detail"]


def test_security_snapshot_rejects_placeholder_tenant_header(client):
    response = client.get(
        f"/tenant/{TENANT_ID}/security-snapshot",
        headers={
            "Authorization": f"Bearer {INTERNAL_TOKEN}",
            "X-Tenant-ID": "default",
        },
    )

    assert response.status_code == 400
    assert "X-Tenant-ID" in response.json()["detail"]
