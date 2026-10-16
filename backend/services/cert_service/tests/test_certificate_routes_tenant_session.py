"""Focused tenant-session coverage for cert-service user-facing routes."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api import certificates as certificates_api
from app.core import auth as auth_module
from app.core import database as cert_database


TENANT_ID = UUID("00000000-0000-0000-0000-000000000111")


class FakeQuery:
    """Minimal query stub for CA authority listing."""

    def __init__(self, results):
        self.results = results

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self.results


class FakeDB:
    """Minimal DB stub for tenant-session route tests."""

    def __init__(self, ca_results):
        self.ca_results = ca_results

    def query(self, model):
        return FakeQuery(self.ca_results)


def _make_ca(name: str, tenant_id):
    return SimpleNamespace(
        id=uuid4(),
        name=name,
        type="step-ca",
        status="active",
        tenant_id=tenant_id,
        created_at=datetime.now(timezone.utc),
    )


def _make_certificate(tenant_id: UUID):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        serial_number="serial-1",
        tenant_id=tenant_id,
        subject_cn="svc.internal",
        dns_names=["svc.internal"],
        ip_addresses=["10.0.0.5"],
        usage="service",
        service_type="siem-agent",
        agent_id=None,
        issued_at=now,
        expires_at=now + timedelta(days=30),
        revoked_at=None,
        revocation_reason=None,
        status="issued",
    )


@pytest.fixture
def client(monkeypatch):
    """Create a client that requires tenant-scoped DB access."""
    app.router.on_startup.clear()
    certificate = _make_certificate(TENANT_ID)
    fake_db = FakeDB([
        _make_ca("Tenant CA", TENANT_ID),
        _make_ca("Shared CA", None),
    ])

    def override_current_tenant():
        return TENANT_ID

    def unexpected_get_db():
        raise AssertionError("Route used get_db instead of get_tenant_session")
        yield  # pragma: no cover

    def override_tenant_session():
        yield fake_db

    def fake_verify_token(token: str):
        return {
            "tenant_id": str(TENANT_ID),
            "user_id": "user-1",
            "roles": ["TENANT_ADMIN"],
        }

    app.dependency_overrides[certificates_api.get_current_tenant] = override_current_tenant
    app.dependency_overrides[cert_database.get_db] = unexpected_get_db
    app.dependency_overrides[certificates_api.get_db] = unexpected_get_db
    app.dependency_overrides[certificates_api.get_tenant_session] = override_tenant_session
    monkeypatch.setattr(auth_module, "verify_token", fake_verify_token)

    try:
        with TestClient(app) as test_client:
            yield test_client, fake_db, certificate
    finally:
        app.dependency_overrides.clear()


def test_user_facing_certificate_routes_use_tenant_session(client, monkeypatch):
    test_client, fake_db, certificate = client
    observed = {}

    class DummyCertificateService:
        def __init__(self, db, tenant_id=None):
            assert db is fake_db
            observed.setdefault("tenants", []).append(tenant_id)

        def renew_certificate(self, certificate_id):
            assert certificate_id == certificate.id
            return {
                "certificate_id": certificate.id,
                "certificate_pem": "renewed-cert",
                "ca_chain_pem": "chain",
                "serial_number": "renewed-serial",
                "expires_at": certificate.expires_at + timedelta(days=30),
            }

        def revoke_certificate(self, certificate_id, reason):
            assert certificate_id == certificate.id
            return {
                "certificate_id": certificate.id,
                "status": "revoked",
                "revoked_at": datetime.now(timezone.utc),
            }

        def list_certificates(self, status=None, usage=None, limit=50, offset=0):
            return [certificate], 1

        def get_certificate(self, certificate_id):
            assert certificate_id == certificate.id
            return certificate

        def create_bootstrap_token(self, tenant_id, agent_id=None, ttl_hours=None):
            assert tenant_id == TENANT_ID
            return {
                "token": "bootstrap-token",
                "token_id": uuid4(),
                "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
            }

    monkeypatch.setattr(certificates_api, "CertificateService", DummyCertificateService)

    ca_response = test_client.get("/api/v1/ca")
    assert ca_response.status_code == 200
    assert len(ca_response.json()) == 2

    renew_response = test_client.post(
        "/api/v1/certificates/renew",
        json={"certificate_id": str(certificate.id)},
    )
    assert renew_response.status_code == 200
    assert renew_response.json()["certificate_id"] == str(certificate.id)

    auth_header = {"Authorization": "Bearer test-token"}
    revoke_response = test_client.post(
        f"/api/v1/certificates/{certificate.id}/revoke",
        json={"reason": "superseded"},
        headers=auth_header,
    )
    assert revoke_response.status_code == 200
    assert revoke_response.json()["status"] == "revoked"

    list_response = test_client.get("/api/v1/certificates")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = test_client.get(f"/api/v1/certificates/{certificate.id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == str(certificate.id)

    bootstrap_response = test_client.post(
        "/api/v1/bootstrap-tokens",
        json={"agent_id": "agent-1", "ttl_hours": 24},
        headers=auth_header,
    )
    assert bootstrap_response.status_code == 200
    assert bootstrap_response.json()["token"] == "bootstrap-token"

    assert observed["tenants"] == [TENANT_ID] * 6
