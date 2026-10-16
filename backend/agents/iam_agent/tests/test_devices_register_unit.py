import json

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
        "roles": ["TENANT_ADMIN"],
        "payload": {"sub": "test-user"},
    }


async def _fake_resolve_user_id_from_email(_email, _realm_name):
    return None


@pytest.fixture
def client(monkeypatch):
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
    monkeypatch.setattr(devices, "_resolve_user_id_from_email", _fake_resolve_user_id_from_email)

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM assets"))

    return TestClient(app)


def auth_headers():
    return {"Authorization": "Bearer fake-token"}


def test_register_device_upsert(client):
    payload = {
        "device_id": "SG-LAPTOP-UNIT",
        "device_type": "laptop",
        "name": "Unit Test Laptop",
        "operating_system": "Ubuntu",
        "os_version": "22.04",
        "owner_email": "user@example.com",
        "trust_status": "trusted",
    }

    r1 = client.post("/api/v1/devices/register", headers=auth_headers(), json=payload)
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    assert body1["device_id"] == payload["device_id"]
    assert body1["device_type"] == "laptop"
    assert body1["trust_status"] == "unknown"

    payload_update = {**payload, "trust_status": "revoked", "ip_address": "10.0.0.5"}
    r2 = client.post("/api/v1/devices/register", headers=auth_headers(), json=payload_update)
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert body2["trust_status"] == "unknown"
    assert body2.get("ip_address") == "10.0.0.5"


def test_register_device_rejects_invalid_trust(client):
    payload = {
        "device_id": "SG-LAPTOP-BAD",
        "device_type": "laptop",
        "trust_status": "bogus",
    }
    r = client.post("/api/v1/devices/register", headers=auth_headers(), json=payload)
    assert r.status_code == 422, r.text
