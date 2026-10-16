from pathlib import Path
import sys
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

from app.api import launch_readiness as launch_api  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import get_tenant_session  # noqa: E402
from app.main import app  # noqa: E402
from app.services.launch_readiness import launch_readiness_service  # noqa: E402


def _sqlite_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return sessionmaker(bind=engine)()


def test_launch_readiness_controls_default_to_platform_flags(monkeypatch):
    tenant_id = str(uuid4())
    db = _sqlite_session()
    monkeypatch.setattr(settings, "COMPLIANCE_MULTI_FRAMEWORK_ENABLED", False)
    monkeypatch.setattr(settings, "COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED", True)
    monkeypatch.setattr(settings, "COMPLIANCE_AGENT_ENABLED", True)

    settings_payload = launch_readiness_service.get_admin_settings(db, tenant_id)

    assert settings_payload["controls"]["multi_framework_selection"]["effective_enabled"] is False
    assert settings_payload["controls"]["multi_framework_selection"]["mutable_by_admin"] is False
    assert "COMPLIANCE_MULTI_FRAMEWORK_ENABLED" in settings_payload["controls"]["multi_framework_selection"]["blocked_reason"]
    assert settings_payload["controls"]["durable_evidence_repository"]["effective_enabled"] is True
    assert settings_payload["controls"]["compliance_agent_workflows"]["effective_enabled"] is True


def test_launch_readiness_admin_update_persists_tenant_disable(monkeypatch):
    tenant_id = str(uuid4())
    db = _sqlite_session()
    monkeypatch.setattr(settings, "COMPLIANCE_MULTI_FRAMEWORK_ENABLED", True)
    monkeypatch.setattr(settings, "COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED", True)
    monkeypatch.setattr(settings, "COMPLIANCE_AGENT_ENABLED", True)

    updated = launch_readiness_service.update_admin_settings(
        db,
        tenant_id,
        {"multi_framework_selection": False, "compliance_agent_workflows": False},
        actor_id="admin-1",
    )

    assert updated["controls"]["multi_framework_selection"]["platform_enabled"] is True
    assert updated["controls"]["multi_framework_selection"]["requested_enabled"] is False
    assert updated["controls"]["multi_framework_selection"]["effective_enabled"] is False
    assert updated["controls"]["durable_evidence_repository"]["effective_enabled"] is True
    assert updated["controls"]["compliance_agent_workflows"]["effective_enabled"] is False


def test_launch_readiness_admin_settings_route_requires_admin_role(monkeypatch):
    tenant_id = str(uuid4())
    db = _sqlite_session()

    def override_tenant_session():
        yield db

    app.dependency_overrides[launch_api.get_current_tenant] = lambda: tenant_id
    app.dependency_overrides[get_tenant_session] = override_tenant_session
    app.dependency_overrides[launch_api.get_current_payload] = lambda: {
        "tenant_id": tenant_id,
        "user_id": "viewer-1",
        "roles": ["viewer"],
    }

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/compliance/admin/settings")
    finally:
        app.dependency_overrides.clear()
        db.close()

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient role for compliance launch controls"


def test_launch_readiness_admin_settings_route_updates_controls(monkeypatch):
    tenant_id = str(uuid4())
    db = _sqlite_session()
    monkeypatch.setattr(settings, "COMPLIANCE_MULTI_FRAMEWORK_ENABLED", True)
    monkeypatch.setattr(settings, "COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED", True)
    monkeypatch.setattr(settings, "COMPLIANCE_AGENT_ENABLED", True)

    def override_tenant_session():
        yield db

    app.dependency_overrides[launch_api.get_current_tenant] = lambda: tenant_id
    app.dependency_overrides[get_tenant_session] = override_tenant_session
    app.dependency_overrides[launch_api.get_current_payload] = lambda: {
        "tenant_id": tenant_id,
        "user_id": "admin-1",
        "roles": ["tenant_admin"],
    }

    try:
        with TestClient(app) as client:
            response = client.put(
                "/api/v1/compliance/admin/settings",
                json={"multi_framework_selection": False, "compliance_agent_workflows": False},
            )
    finally:
        app.dependency_overrides.clear()
        db.close()

    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_id"] == tenant_id
    assert payload["controls"]["multi_framework_selection"]["effective_enabled"] is False
    assert payload["controls"]["compliance_agent_workflows"]["effective_enabled"] is False
