from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import ai_features
from app.api.auth import get_keycloak_client
from app.api.request_context import RequestContext, get_current_request_context


class KeycloakClientSpy:
    def list_users(self):
        return [{"id": "user-1", "username": "alice", "mfa_enabled": True}]

    def get_user(self, user_id):
        return {"id": user_id, "username": "alice"}

    def get_user_roles(self, _user_id):
        return [{"name": "ROLE_USER"}]

    def get_authorization_policies(self):
        return [{"id": "policy-1"}]


class AnomalyServiceSpy:
    def __init__(self):
        self.calls = []

    def detect_access_pattern_anomalies(self, user_id, access_history, tenant_id):
        self.calls.append((user_id, access_history, tenant_id))
        return [{"severity": "high", "user_id": user_id}]


class RiskServiceSpy:
    def __init__(self):
        self.user_calls = []
        self.tenant_calls = []

    def calculate_user_risk_score(self, user_id, user_data, access_history, anomalies, tenant_id):
        self.user_calls.append((user_id, user_data, access_history, anomalies, tenant_id))
        return {
            "scope": "user",
            "entity_id": user_id,
            "tenant_id": tenant_id,
            "overall_risk_score": 42.0,
            "risk_level": "medium",
            "risk_factors": {},
            "recommendations": [],
            "calculated_at": datetime.now(timezone.utc),
        }

    def calculate_tenant_risk_score(self, tenant_id, users, entitlements, anomalies):
        self.tenant_calls.append((tenant_id, users, entitlements, anomalies))
        return {
            "tenant_id": tenant_id,
            "overall_risk_score": 35.0,
            "risk_level": "medium",
            "risk_factors": {},
            "recommendations": [],
            "calculated_at": datetime.now(timezone.utc),
        }


class RecommendationEngineSpy:
    def __init__(self):
        self.role_calls = []
        self.optimization_calls = []
        self.compliance_calls = []
        self.ai_calls = []

    def recommend_role_mining(self, users, entitlements, tenant_id):
        self.role_calls.append((users, entitlements, tenant_id))
        return []

    def recommend_access_optimization(self, users, access_history, tenant_id):
        self.optimization_calls.append((users, access_history, tenant_id))
        return []

    def recommend_compliance_improvements(self, tenant_id, policies, users, entitlements):
        self.compliance_calls.append((tenant_id, policies, users, entitlements))
        return [{"priority": "high", "title": "Enable MFA"}]

    def generate_ai_recommendations(self, query, context, tenant_id):
        self.ai_calls.append((query, context, tenant_id))
        return {"priority": "medium", "title": "AI Recommendation"}


@pytest.fixture
def request_context():
    return RequestContext(
        tenant_id=uuid4(),
        user_id=str(uuid4()),
    )


@pytest.fixture
def ai_features_test_app(request_context):
    app = FastAPI()
    app.include_router(ai_features.router)
    app.dependency_overrides[get_current_request_context] = lambda: request_context
    return app


@pytest.fixture
def ai_features_client(ai_features_test_app):
    return TestClient(ai_features_test_app)


def _override_dependency(app, dependency, value):
    app.dependency_overrides[dependency] = lambda: value


def test_detect_anomalies_rejects_foreign_body_tenant(
    ai_features_test_app,
    ai_features_client,
):
    _override_dependency(ai_features_test_app, get_keycloak_client, KeycloakClientSpy())
    anomaly_service = AnomalyServiceSpy()
    _override_dependency(ai_features_test_app, ai_features.get_anomaly_service, anomaly_service)

    response = ai_features_client.post(
        "/internal/iam/ai/anomalies/detect",
        headers={"authorization": "Bearer test-token"},
        json={"tenant_id": str(uuid4()), "user_id": "user-1"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert anomaly_service.calls == []


def test_calculate_risk_score_rejects_foreign_body_tenant(
    ai_features_test_app,
    ai_features_client,
):
    _override_dependency(ai_features_test_app, get_keycloak_client, KeycloakClientSpy())
    risk_service = RiskServiceSpy()
    _override_dependency(ai_features_test_app, ai_features.get_risk_service, risk_service)

    response = ai_features_client.post(
        "/internal/iam/ai/risk/score",
        headers={"authorization": "Bearer test-token"},
        json={"scope": "tenant", "tenant_id": str(uuid4())},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert risk_service.user_calls == []
    assert risk_service.tenant_calls == []


def test_list_user_risk_scores_rejects_foreign_query_tenant(
    ai_features_test_app,
    ai_features_client,
):
    _override_dependency(ai_features_test_app, get_keycloak_client, KeycloakClientSpy())
    risk_service = RiskServiceSpy()
    _override_dependency(ai_features_test_app, ai_features.get_risk_service, risk_service)

    response = ai_features_client.get(
        f"/internal/iam/ai/risk/users?tenant_id={uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert risk_service.user_calls == []


def test_get_recommendations_rejects_foreign_body_tenant(
    ai_features_test_app,
    ai_features_client,
):
    _override_dependency(ai_features_test_app, get_keycloak_client, KeycloakClientSpy())
    engine = RecommendationEngineSpy()
    _override_dependency(ai_features_test_app, ai_features.get_recommendation_engine, engine)

    response = ai_features_client.post(
        "/internal/iam/ai/recommendations",
        headers={"authorization": "Bearer test-token"},
        json={"type": "compliance", "tenant_id": str(uuid4())},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert engine.compliance_calls == []


def test_compliance_recommendations_default_to_authenticated_tenant(
    ai_features_test_app,
    ai_features_client,
    request_context,
):
    _override_dependency(ai_features_test_app, get_keycloak_client, KeycloakClientSpy())
    engine = RecommendationEngineSpy()
    _override_dependency(ai_features_test_app, ai_features.get_recommendation_engine, engine)

    response = ai_features_client.get(
        "/internal/iam/ai/recommendations/compliance",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 501
    assert engine.compliance_calls == []
