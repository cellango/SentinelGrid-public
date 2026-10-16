from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import policies
from app.api.request_context import get_tenant_session
from app.models.policies import Action, Policy, PolicyEvaluationResult


class FakePolicyService:
    last_init = None

    def __init__(self, db, tenant_id, realm_name):
        type(self).last_init = {
            "db": db,
            "tenant_id": tenant_id,
            "realm_name": realm_name,
        }
        self.db = db
        self.tenant_id = tenant_id
        self.realm_name = realm_name

    def _policy(self):
        now = datetime.now(timezone.utc)
        return Policy(
            id=uuid4(),
            tenant_id=self.tenant_id,
            name="mfa-required",
            display_name="Require MFA",
            description="Require MFA for privileged sign-on",
            policy_type="signon",
            scope="tenant",
            scope_id=None,
            policy_data={"rules": []},
            is_active=True,
            priority=100,
            created_by="policy-user",
            created_at=now,
            updated_at=now,
        )

    def list_seed_policies(self):
        return [self._policy()]

    def list_policies(self, policy_type=None, scope=None, scope_id=None):
        return [self._policy()]

    def evaluate_policy(self, policy_type, context):
        return PolicyEvaluationResult(
            result="allow",
            policy_id=uuid4(),
            matched_rules=["rule-1"],
            actions=[Action(type="allow")],
            explanation=f"evaluated {policy_type}",
        )


@pytest.fixture
def tenant_id():
    return uuid4()


@pytest.fixture
def policies_user_info(tenant_id):
    return {
        "user_id": "policy-user",
        "tenant_id": str(tenant_id),
        "realm_name": "demo",
    }


@pytest.fixture
def policies_test_app(monkeypatch, policies_user_info):
    app = FastAPI()
    app.include_router(policies.router)

    fake_db = object()

    def _get_tenant_session_override():
        yield fake_db

    app.dependency_overrides[policies.get_current_user_info] = lambda: policies_user_info
    app.dependency_overrides[policies.get_current_user_id] = lambda: policies_user_info["user_id"]
    app.dependency_overrides[get_tenant_session] = _get_tenant_session_override
    monkeypatch.setattr(policies, "PolicyService", FakePolicyService)

    return app, fake_db


@pytest.fixture
def policies_client(policies_test_app):
    app, _ = policies_test_app
    return TestClient(app)


def test_list_policies_uses_tenant_scoped_session(policies_test_app, policies_client, tenant_id):
    _, fake_db = policies_test_app

    response = policies_client.get("/api/iam-portal/policies")

    assert response.status_code == 200
    assert response.json()[0]["tenant_id"] == str(tenant_id)
    assert FakePolicyService.last_init == {
        "db": fake_db,
        "tenant_id": tenant_id,
        "realm_name": "demo",
    }


def test_list_policy_bundles_uses_tenant_scoped_session(policies_test_app, policies_client, tenant_id):
    _, fake_db = policies_test_app

    response = policies_client.get("/api/iam-portal/policies/bundles")

    assert response.status_code == 200
    assert response.json()[0]["tenant_id"] == str(tenant_id)
    assert FakePolicyService.last_init == {
        "db": fake_db,
        "tenant_id": tenant_id,
        "realm_name": "demo",
    }


def test_evaluate_policy_uses_tenant_scoped_session(policies_test_app, policies_client, tenant_id):
    _, fake_db = policies_test_app

    response = policies_client.post(
        "/api/iam-portal/policies/evaluate",
        params={"policy_type": "signon"},
        json={"user_id": "policy-user", "action": "signon"},
    )

    assert response.status_code == 200
    assert response.json()["result"] == "allow"
    assert FakePolicyService.last_init == {
        "db": fake_db,
        "tenant_id": tenant_id,
        "realm_name": "demo",
    }
