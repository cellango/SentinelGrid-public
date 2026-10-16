"""Focused tenant-isolation coverage for cert-service enrollment routes."""

from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4
import os
import sys

import pytest
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

os.environ.setdefault("DB_HOST", "localhost")

from app.main import app
from app.api import certificates as certificates_api


TENANT_ID = UUID("00000000-0000-0000-0000-000000000111")


@pytest.fixture
def client():
    app.router.on_startup.clear()

    def override_service_tenant():
        return TENANT_ID

    def override_service_db():
        yield object()

    def override_agent_tenant():
        return TENANT_ID

    def override_agent_db():
        yield object()

    app.dependency_overrides[certificates_api.resolve_service_enrollment_tenant] = override_service_tenant
    app.dependency_overrides[certificates_api.get_service_enrollment_tenant_session] = override_service_db
    app.dependency_overrides[certificates_api.resolve_agent_enrollment_tenant] = override_agent_tenant
    app.dependency_overrides[certificates_api.get_agent_enrollment_tenant_session] = override_agent_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_enroll_service_uses_resolved_tenant(client, monkeypatch):
    observed = {}

    class DummyCertificateService:
        def __init__(self, db, tenant_id=None):
            observed["init"] = (db, tenant_id)

        def enroll_service(self, **kwargs):
            observed["call"] = kwargs
            return {
                "certificate_id": uuid4(),
                "certificate_pem": "cert-pem",
                "private_key_pem": "key-pem",
                "ca_chain_pem": "chain-pem",
                "serial_number": "serial-1",
                "expires_at": datetime.utcnow() + timedelta(days=30),
                "spki_fingerprint": "fingerprint-1",
            }

    monkeypatch.setattr(certificates_api, "CertificateService", DummyCertificateService)

    response = client.post(
        "/api/v1/certificates/enroll-service",
        json={
            "tenant_id": str(TENANT_ID),
            "service_id": "svc-1",
            "service_type": "siem-agent",
            "subject_cn": "svc.internal",
            "dns_names": ["svc.internal"],
            "ip_addresses": [],
        },
    )

    assert response.status_code == 200
    assert observed["init"][1] == TENANT_ID
    assert observed["call"]["service_id"] == "svc-1"
    assert observed["call"]["service_type"] == "siem-agent"


def test_enroll_agent_uses_bootstrap_resolved_tenant(client, monkeypatch):
    observed = {}

    class DummyCertificateService:
        def __init__(self, db, tenant_id=None):
            observed["init"] = (db, tenant_id)

        def enroll_agent(self, **kwargs):
            observed["call"] = kwargs
            return {
                "certificate_id": uuid4(),
                "certificate_pem": "cert-pem",
                "private_key_pem": "key-pem",
                "ca_chain_pem": "chain-pem",
                "serial_number": "serial-2",
                "expires_at": datetime.utcnow() + timedelta(days=30),
            }

    monkeypatch.setattr(certificates_api, "CertificateService", DummyCertificateService)

    response = client.post(
        "/api/v1/certificates/enroll-agent",
        json={
            "bootstrap_token": "bootstrap-token",
            "agent_id": "agent-1",
            "hostname": "agent-host",
            "ip": "10.0.0.1",
            "dns_names": ["agent-host"],
        },
    )

    assert response.status_code == 200
    assert observed["init"][1] == TENANT_ID
    assert observed["call"]["tenant_id"] == TENANT_ID
    assert observed["call"]["agent_id"] == "agent-1"
