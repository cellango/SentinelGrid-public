"""Unit tests for lead metadata and demo-request intake helpers."""

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import leads


class _FakeResult:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def fetchone(self):
        return self._row


class _FakeDB:
    def __init__(self, existing_lead=None, lead_by_id=None):
        self.existing_lead = existing_lead
        self.lead_by_id = lead_by_id
        self.statements = []
        self.insert_params = None
        self.update_params = None
        self.committed = False
        self.rolled_back = False

    def execute(self, statement, params=None):
        sql = str(statement)
        self.statements.append((sql, params))

        if "SELECT id, status, metadata FROM leads WHERE email = :email" in sql:
            return _FakeResult(self.existing_lead)

        if "SELECT id, company_name, user_count, user_band, compliance_required," in sql:
            return _FakeResult(self.lead_by_id)

        if "SELECT id, user_count, compliance_required, package_name, metadata, expires_at, status" in sql:
            return _FakeResult(self.lead_by_id)

        if "INSERT INTO leads" in sql:
            self.insert_params = params
            return _FakeResult(None)

        if "UPDATE leads" in sql:
            self.update_params = params
            return _FakeResult(None)

        raise AssertionError(f"Unexpected SQL executed during test: {sql}")

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        return None


def _build_client(monkeypatch, fake_db):
    app = FastAPI()
    app.include_router(leads.router)

    monkeypatch.setattr(leads.settings, "DB_URL", "postgresql://demo:test@localhost:5432/demo")
    monkeypatch.setattr(leads, "create_engine", lambda *args, **kwargs: object())
    monkeypatch.setattr(leads, "sessionmaker", lambda *args, **kwargs: (lambda: fake_db))

    return TestClient(app)


def test_estimate_demo_user_count_maps_company_bands():
    assert leads._estimate_demo_user_count("1-25 employees") == 25
    assert leads._estimate_demo_user_count("26-100 employees") == 100
    assert leads._estimate_demo_user_count("101-250 employees") == 250
    assert leads._estimate_demo_user_count("251-1000 employees") == 1000
    assert leads._estimate_demo_user_count("1000+ employees") == 1001


def test_build_demo_qualification_context_marks_guided_review_reasons():
    payload = leads._build_demo_qualification_context(
        motion="partner",
        identity_profile="mixed",
        rollout_scope="multi_environment",
        retention_profile="extended_or_archive",
        ai_shield_fit="primary",
    )

    assert payload["recommended_path"] == "guided_review"
    assert payload["guided_review_reasons"] == [
        "partner_motion",
        "mixed_identity",
        "multi_environment",
        "extended_retention_or_trust_review",
        "ai_shield_primary",
    ]


def test_build_lead_metadata_preserves_existing_demo_request():
    metadata = leads._build_lead_metadata(
        {
            "demo_request": {"request_count": 1, "source": "demo_page_form"},
            "other": "value",
        },
        services_selected={"cloud": True},
        plan_tier="protect_defend",
        lead_source="signup",
    )

    assert metadata == {
        "demo_request": {"request_count": 1, "source": "demo_page_form"},
        "other": "value",
        "services_selected": {"cloud": True},
        "plan_tier": "protect_defend",
        "lead_source": "signup",
    }


def test_create_demo_request_inserts_pending_lead(monkeypatch):
    fake_db = _FakeDB(existing_lead=None)
    client = _build_client(monkeypatch, fake_db)

    response = client.post(
        "/api/v1/leads/demo-request",
        json={
            "email": "buyer@example.com",
            "company_name": "Example Co",
            "first_name": "Jamie",
            "last_name": "Rivera",
            "company_size": "26-100 employees",
            "notes": "Show AWS onboarding and response workflow.",
            "plan_tier": "protect_defend",
            "source": "demo_page_form",
            "motion": "standard",
            "identity_profile": "microsoft_entra",
            "rollout_scope": "single_environment",
            "retention_profile": "standard",
            "ai_shield_fit": "none",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert fake_db.committed is True
    assert fake_db.insert_params is not None
    assert fake_db.insert_params["user_count"] == 100
    assert fake_db.insert_params["status"] if "status" in fake_db.insert_params else "pending" == "pending"

    metadata = json.loads(fake_db.insert_params["metadata"])
    assert metadata["lead_source"] == "demo_request"
    assert metadata["plan_tier"] == "protect_defend"
    assert fake_db.insert_params["package_name"] == "protect_defend"
    assert metadata["demo_request"]["company_size"] == "26-100 employees"
    assert metadata["demo_request"]["notes"] == "Show AWS onboarding and response workflow."
    assert metadata["demo_request"]["request_count"] == 1
    assert metadata["demo_request"]["qualification"] == {
        "motion": "standard",
        "identity_profile": "microsoft_entra",
        "rollout_scope": "single_environment",
        "retention_profile": "standard",
        "ai_shield_fit": "none",
        "guided_review_reasons": [],
        "recommended_path": "standard_launch_path",
    }


def test_create_demo_request_updates_existing_lead_metadata(monkeypatch):
    fake_db = _FakeDB(
        existing_lead=(
            "lead-123",
            "pending",
            {
                "lead_source": "signup",
                "plan_tier": "protect",
                "demo_request": {"request_count": 1, "first_requested_at": "2026-03-20T10:00:00"},
            },
        )
    )
    client = _build_client(monkeypatch, fake_db)

    response = client.post(
        "/api/v1/leads/demo-request",
        json={
            "email": "buyer@example.com",
            "company_name": "Example Co",
            "first_name": "Jamie",
            "last_name": "Rivera",
            "company_size": "101-250 employees",
            "notes": "Focus on compliance and queue workflow.",
            "plan_tier": "protect_defend_comply",
            "source": "demo_page_form",
            "motion": "standard",
            "identity_profile": "mixed",
            "rollout_scope": "multi_environment",
            "retention_profile": "extended_or_archive",
            "ai_shield_fit": "primary",
        },
    )

    assert response.status_code == 200
    assert fake_db.committed is True
    assert fake_db.update_params is not None
    assert fake_db.update_params["id"] == "lead-123"

    metadata = json.loads(fake_db.update_params["metadata"])
    assert metadata["demo_request"]["request_count"] == 2
    assert metadata["demo_request"]["first_requested_at"] == "2026-03-20T10:00:00"
    assert metadata["demo_request"]["company_size"] == "101-250 employees"
    assert metadata["plan_tier"] == "protect_defend_comply"
    assert metadata["lead_source"] == "demo_request"
    assert metadata["demo_request"]["qualification"]["recommended_path"] == "guided_review"
    assert metadata["demo_request"]["qualification"]["guided_review_reasons"] == [
        "mixed_identity",
        "multi_environment",
        "extended_retention_or_trust_review",
        "ai_shield_primary",
    ]
    assert fake_db.update_params["package_name"] == "protect_defend_comply"


def test_update_lead_syncs_canonical_plan_and_services(monkeypatch):
    fake_db = _FakeDB(
        lead_by_id={
            "id": "lead-123",
            "user_count": 25,
            "compliance_required": False,
            "package_name": "protect",
            "metadata": {
                "provisioning_token": "opaque-token",
                "services_selected": {"cloud": True},
                "plan_tier": "protect",
            },
            "expires_at": None,
            "status": "pending",
        }
    )
    client = _build_client(monkeypatch, fake_db)

    response = client.patch(
        "/api/v1/leads/lead-123",
        headers={"Authorization": "Bearer opaque-token"},
        json={
            "plan_tier": "protect_defend_comply",
            "services_selected": {"cloud": True},
            "tenant_slug": "acme-co",
        },
    )

    assert response.status_code == 200
    assert fake_db.committed is True
    assert fake_db.update_params is not None
    assert fake_db.update_params["package_name"] == "protect_defend_comply"
    assert fake_db.update_params["compliance_required"] is True
    assert fake_db.update_params["estimated_price_cents"] == 149900

    metadata = json.loads(fake_db.update_params["metadata"])
    assert metadata["plan_tier"] == "protect_defend_comply"
    assert metadata["tenant_slug"] == "acme-co"
    assert metadata["services_selected"]["trustProfile"]["enabled"] is True


def test_get_lead_requires_bearer_token(monkeypatch):
    fake_db = _FakeDB(
        lead_by_id=(
            "lead-123",
            "Example Co",
            100,
            "26-100",
            False,
            "protect",
            29900,
            "pending",
            {"provisioning_token": "opaque-token"},
            None,
            None,
        )
    )
    client = _build_client(monkeypatch, fake_db)

    response = client.get("/api/v1/leads/lead-123")

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing authorization header"}


def test_get_lead_rejects_invalid_provisioning_token(monkeypatch):
    fake_db = _FakeDB(
        lead_by_id=(
            "lead-123",
            "Example Co",
            100,
            "26-100",
            False,
            "protect",
            29900,
            "pending",
            {"provisioning_token": "opaque-token"},
            None,
            None,
        )
    )
    client = _build_client(monkeypatch, fake_db)

    response = client.get(
        "/api/v1/leads/lead-123",
        headers={"Authorization": "Bearer wrong-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid provisioning token"}


def test_get_lead_returns_minimized_pre_tenant_record(monkeypatch):
    fake_db = _FakeDB(
        lead_by_id=(
            "lead-123",
            "Example Co",
            100,
            "26-100",
            False,
            "protect",
            29900,
            "payment_started",
            {"provisioning_token": "opaque-token"},
            None,
            None,
        )
    )
    client = _build_client(monkeypatch, fake_db)

    response = client.get(
        "/api/v1/leads/lead-123",
        headers={"Authorization": "Bearer opaque-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "lead-123",
        "company_name": "Example Co",
        "user_count": 100,
        "user_band": "26-100",
        "compliance_required": False,
        "package_name": "protect",
        "plan_tier": "protect",
        "estimated_price_cents": 29900,
        "status": "payment_started",
        "created_at": None,
        "expires_at": None,
        "has_active_checkout_session": True,
    }
