import json
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import devices


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(engine, "connect")
def _register_sqlite_now(dbapi_connection, _connection_record):
    dbapi_connection.create_function("NOW", 0, lambda: "2026-03-29T00:00:00")

with engine.connect() as conn:
    conn.execute(
        text(
            """
            CREATE TABLE assets (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                asset_id TEXT NOT NULL,
                asset_type TEXT,
                name TEXT,
                operating_system TEXT,
                os_version TEXT,
                ip_address TEXT,
                owner TEXT,
                user_id TEXT,
                department TEXT,
                source TEXT,
                metadata TEXT,
                compliance_status TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE iam_audit_log (
                tenant_id TEXT,
                realm_name TEXT,
                action TEXT,
                actor_user_id TEXT,
                actor_email TEXT,
                target_user_id TEXT,
                details TEXT
            );
            """
        )
    )
    conn.commit()


async def _fake_get_token_data(_token):
    return {
        "tenant_id": "tenant-test",
        "realm_name": "demo",
        "user_id": "test-user",
        "email": "user@example.com",
        "roles": ["TENANT_ADMIN"],
        "payload": {"sub": "test-user", "email": "user@example.com"},
    }


async def _fake_logout_user_sessions(_realm_name, _user_id):
    return True


def _insert_device(asset_id: str):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO assets (
                    id, tenant_id, asset_id, asset_type, name,
                    operating_system, os_version, ip_address,
                    owner, user_id, source, metadata, compliance_status
                ) VALUES (
                    :id, :tenant_id, :asset_id, :asset_type, :name,
                    :operating_system, :os_version, :ip_address,
                    :owner, :user_id, 'manual', :metadata, :compliance_status
                )
                """
            ),
            {
                "id": str(uuid4()),
                "tenant_id": "tenant-test",
                "asset_id": asset_id,
                "asset_type": "laptop",
                "name": "Unit Test Laptop",
                "operating_system": "Ubuntu",
                "os_version": "22.04",
                "ip_address": "10.0.0.5",
                "owner": "user@example.com",
                "user_id": "test-user",
                "metadata": json.dumps({"trust_status": "trusted"}),
                "compliance_status": "compliant",
            },
        )


@pytest.fixture
def devices_client(monkeypatch):
    app = FastAPI()
    app.include_router(devices.router)

    def _get_tenant_session_override():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[devices.get_tenant_session] = _get_tenant_session_override
    monkeypatch.setattr(devices, "get_token_data", _fake_get_token_data)
    monkeypatch.setattr(devices, "_logout_user_sessions", _fake_logout_user_sessions)

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM assets"))

    return TestClient(app)


def auth_headers():
    return {"Authorization": "Bearer fake-token"}


def test_list_devices_uses_tenant_scoped_session(devices_client):
    _insert_device("SG-LIST-DEVICE")

    response = devices_client.get("/api/v1/devices", headers=auth_headers())

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["device_id"] == "SG-LIST-DEVICE"


def test_set_device_trust_uses_tenant_scoped_session(devices_client):
    _insert_device("SG-TRUST-DEVICE")

    response = devices_client.post(
        "/api/v1/devices/SG-TRUST-DEVICE/trust",
        headers=auth_headers(),
        json={"trust_status": "untrusted", "reason": "risk"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["device_id"] == "SG-TRUST-DEVICE"


def test_revoke_device_uses_tenant_scoped_session(devices_client):
    _insert_device("SG-REVOKE-DEVICE")

    response = devices_client.post(
        "/api/v1/devices/SG-REVOKE-DEVICE/revoke",
        headers=auth_headers(),
    )

    assert response.status_code == 200, response.text
    assert response.json()["success"] is True


def test_report_device_uses_tenant_scoped_session(devices_client):
    _insert_device("SG-REPORT-DEVICE")

    response = devices_client.post(
        "/api/v1/devices/SG-REPORT-DEVICE/report",
        headers=auth_headers(),
        json={"report_type": "lost", "note": "left at airport"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["device_id"] == "SG-REPORT-DEVICE"
