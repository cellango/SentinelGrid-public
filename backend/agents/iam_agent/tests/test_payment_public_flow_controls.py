import json
from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import payment


class FakeResult:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def fetchone(self):
        return self._row


class FakeDB:
    def __init__(self, lead):
        self.lead = dict(lead)
        self.commits = 0
        self.closed = False

    def execute(self, statement, params=None):
        sql = str(statement)
        lowered = sql.lower()
        params = params or {}

        if "from leads" in lowered:
            return FakeResult(dict(self.lead))

        if "update leads set status = 'payment_started'" in lowered:
            self.lead["status"] = "payment_started"
            return FakeResult(None)

        if "update leads set stripe_session_id" in lowered:
            self.lead["stripe_session_id"] = params["session_id"]
            return FakeResult(None)

        return FakeResult(None)

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


@pytest.fixture
def lead_record():
    provisioning_token = "opaque-provisioning-token"
    return {
        "id": "lead-123",
        "email": "buyer@example.com",
        "company_name": "Acme",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "password_hash": "hash",
        "user_count": 25,
        "user_band": "1-25",
        "compliance_required": False,
        "package_name": "protect",
        "estimated_price_cents": 25000,
        "status": "pending",
        "stripe_session_id": None,
        "metadata": {
            "provisioning_token": provisioning_token,
            "services_selected": {},
        },
        "expires_at": datetime.utcnow() + timedelta(days=7),
    }


@pytest.fixture
def payment_test_app(monkeypatch, lead_record):
    fake_db = FakeDB(lead_record)

    def fake_sessionmaker(*args, **kwargs):
        return lambda: fake_db

    monkeypatch.setattr(payment, "create_engine", lambda *args, **kwargs: object())
    monkeypatch.setattr(payment, "sessionmaker", fake_sessionmaker)
    monkeypatch.setattr(payment.settings, "DB_URL", "postgresql://test")
    monkeypatch.setattr(payment.settings, "PAYMENT_DEV_MODE", True)
    monkeypatch.setattr(payment.settings, "STRIPE_SECRET_KEY", None)

    app = FastAPI()
    app.include_router(payment.router)
    app.state.fake_db = fake_db
    return app


@pytest.fixture
def payment_client(payment_test_app):
    return TestClient(payment_test_app)


def test_create_checkout_session_rejects_invalid_provisioning_token(payment_client):
    response = payment_client.post(
        "/api/v1/payment/create-checkout-session",
        json={
            "lead_id": "lead-123",
            "provisioning_token": "wrong-token",
            "billing_period": "monthly",
            "success_url": "https://example.com/success?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": "https://example.com/cancel",
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid provisioning token"}


def test_create_checkout_session_dev_mode_accepts_valid_provisioning_token(
    payment_client,
    payment_test_app,
):
    response = payment_client.post(
        "/api/v1/payment/create-checkout-session",
        json={
            "lead_id": "lead-123",
            "provisioning_token": "opaque-provisioning-token",
            "billing_period": "monthly",
            "success_url": "https://example.com/success?session_id={CHECKOUT_SESSION_ID}",
            "cancel_url": "https://example.com/cancel",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["dev_mode"] is True
    assert payload["session_id"] == "dev_session_lead-123"
    assert payment_test_app.state.fake_db.lead["status"] == "payment_started"
    assert payment_test_app.state.fake_db.lead["stripe_session_id"] == "dev_session_lead-123"


def test_payment_success_rejects_invalid_provisioning_token(payment_client):
    response = payment_client.post(
        "/api/v1/payment/success",
        json={
            "session_id": "dev_session_lead-123",
            "lead_id": "lead-123",
            "provisioning_token": "wrong-token",
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid provisioning token"}


def test_payment_success_rejects_session_mismatch(payment_client, payment_test_app):
    payment_test_app.state.fake_db.lead["status"] = "payment_started"
    payment_test_app.state.fake_db.lead["stripe_session_id"] = "dev_session_lead-123"

    response = payment_client.post(
        "/api/v1/payment/success",
        json={
            "session_id": "dev_session_other",
            "lead_id": "lead-123",
            "provisioning_token": "opaque-provisioning-token",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Checkout session does not match lead"}
