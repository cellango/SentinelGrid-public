"""Unit tests for trust and compliance onboarding prompts."""

import json
import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.api import onboarding


class _FakeResult:
    def fetchone(self):
        return None


class _FakeDB:
    def __init__(self):
        self.statements = []
        self.committed = False
        self.rolled_back = False

    def execute(self, statement, params=None):
        self.statements.append((str(statement), params))
        return _FakeResult()

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def _build_client(fake_db):
    app = FastAPI()
    app.include_router(onboarding.router)
    app.dependency_overrides[onboarding.get_db] = lambda: fake_db
    app.dependency_overrides[onboarding.get_tenant_session] = lambda: fake_db
    app.dependency_overrides[onboarding.get_onboarding_customer_id] = lambda: "tenant-123"
    return TestClient(app)


def test_normalize_trust_profile_infers_enabled_and_dedupes():
    payload = onboarding._normalize_trust_profile(
        {
            "frameworks": ["SOC 2", "soc2", "Customer Questionnaires"],
            "primaryDriver": "Customer Security Review",
            "targetTimeline": "This Quarter",
            "needsEvidenceExports": True,
            "notes": "  Need evidence for procurement.  ",
        }
    )

    assert payload["enabled"] is True
    assert payload["frameworks"] == ["soc2", "customer_questionnaires"]
    assert payload["primaryDriver"] == "customer_security_review"
    assert payload["targetTimeline"] == "this_quarter"
    assert payload["needsEvidenceExports"] is True
    assert payload["notes"] == "Need evidence for procurement."


def test_build_trust_announcements_flags_missing_scope():
    announcements = onboarding._build_trust_announcements(
        {
            "enabled": True,
            "frameworks": [],
            "primaryDriver": None,
            "targetTimeline": None,
            "needsEvidenceExports": False,
            "needsQuestionnaireSupport": False,
        }
    )

    announcement_ids = [item["id"] for item in announcements]
    assert "trust-scope" in announcement_ids
    assert "trust-outputs" in announcement_ids


def test_save_trust_profile_persists_onboarding_services(monkeypatch):
    fake_db = _FakeDB()
    client = _build_client(fake_db)

    monkeypatch.setattr(onboarding, "_resolve_progress_key", lambda customer_id, db: customer_id)

    response = client.post(
        "/api/v1/onboarding/trust-profile",
        headers={"X-Tenant-ID": "tenant-123"},
        json={
            "enabled": True,
            "frameworks": ["soc2", "customer_questionnaires"],
            "primaryDriver": "customer_security_review",
            "targetTimeline": "90_days",
            "needsQuestionnaireSupport": True,
            "needsEvidenceExports": True,
            "notes": "Need trust outputs this quarter.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["trustProfile"]["frameworks"] == ["soc2", "customer_questionnaires"]
    assert fake_db.committed is True

    _, params = fake_db.statements[0]
    saved = json.loads(params["services_selected"])
    assert saved["trustProfile"]["enabled"] is True
    assert saved["trustProfile"]["primaryDriver"] == "customer_security_review"
