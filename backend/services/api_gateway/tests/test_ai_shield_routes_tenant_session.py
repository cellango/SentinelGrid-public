from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock

from app.api import routes_ai_shield
from sg_core.db import get_tenant_session
from sg_core.models import Alert, Tenant


class _QueryResult:
    def __init__(self, result):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


def test_ai_shield_ingest_route_uses_tenant_scoped_dependency():
    app = FastAPI()
    app.include_router(routes_ai_shield.router, prefix="/api/v1")
    tenant_uuid = uuid4()

    fake_db = Mock()
    added = []
    fake_db.add.side_effect = lambda obj: added.append(obj)
    fake_db.commit.return_value = None
    fake_db.refresh.side_effect = lambda obj: None

    def query_side_effect(model):
        if model is Alert:
            return _QueryResult(None)
        if model is Tenant:
            return _QueryResult(
                Tenant(
                    id=tenant_uuid,
                    name="Acme",
                    slug="acme",
                    status="active",
                    incident_management_mode="saas_managed",
                )
            )
        raise AssertionError(f"Unexpected model query: {model}")

    fake_db.query.side_effect = query_side_effect

    def _get_db():
        yield fake_db

    app.dependency_overrides[get_tenant_session] = _get_db

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/internal/ai-shield/events",
            headers={
                "Authorization": "Bearer internal-service-token-change-in-production",
                "X-Tenant-ID": str(tenant_uuid),
            },
            json={
                "event_id": "evt-123",
                "org_id": str(tenant_uuid),
                "ai_app_id": "support-assistant",
                "user_id": "owner@example.com",
                "provider": "openai",
                "model": "gpt-4.1",
                "prompt_injection_suspected": True,
                "policy_decision": "blocked",
                "created_at": "2026-03-26T18:15:00Z",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "created"
    assert payload["alert"]["tenant_id"] == str(tenant_uuid)
    assert payload["incident"]["tenant_id"] == str(tenant_uuid)
    assert any(type(item).__name__ == "Alert" for item in added)
    assert any(type(item).__name__ == "Incident" for item in added)
