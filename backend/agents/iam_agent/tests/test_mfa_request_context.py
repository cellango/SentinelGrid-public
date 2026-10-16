from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import mfa
from app.api.request_context import RequestContext, get_current_request_context


class BiometricServiceSpy:
    def __init__(self):
        self.enroll_calls = []
        self.verify_calls = []
        self.get_calls = []
        self.delete_calls = []

    def enroll_biometric(self, user_id, biometric_type, enrollment_data, tenant_id):
        self.enroll_calls.append((user_id, biometric_type, enrollment_data, tenant_id))
        return {
            "user_id": user_id,
            "biometric_type": biometric_type.value,
            "status": "enrolled",
            "enrolled_at": datetime.now(timezone.utc),
            "samples_used": len(enrollment_data.get("samples", [])),
            "message": "ok",
        }

    def verify_biometric(self, user_id, biometric_type, verification_data, tenant_id):
        self.verify_calls.append((user_id, biometric_type, verification_data, tenant_id))
        return {
            "user_id": user_id,
            "biometric_type": biometric_type.value,
            "verified": True,
            "score": 0.95,
            "threshold": 0.8,
            "confidence": "high",
            "reason": None,
            "verified_at": datetime.now(timezone.utc),
        }

    def get_user_biometrics(self, user_id, tenant_id):
        self.get_calls.append((user_id, tenant_id))
        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "biometrics": {},
            "enrolled_count": 0,
            "total_enabled": 3,
        }

    def delete_biometric_enrollment(self, user_id, biometric_type, tenant_id):
        self.delete_calls.append((user_id, biometric_type, tenant_id))
        return {
            "user_id": user_id,
            "biometric_type": biometric_type.value,
            "status": "deleted",
            "deleted_at": datetime.now(timezone.utc).isoformat(),
        }


class AdaptiveAuthServiceSpy:
    def __init__(self):
        self.risk_calls = []
        self.requirement_calls = []
        self.verify_calls = []

    def calculate_risk_score(self, user_id, auth_context, tenant_id):
        self.risk_calls.append((user_id, auth_context, tenant_id))
        return {
            "user_id": user_id,
            "risk_score": 0.4,
            "risk_level": "medium",
            "risk_factors": {},
            "required_factors": ["password"],
            "policies": {},
            "calculated_at": datetime.now(timezone.utc),
        }

    def determine_auth_requirements(self, user_id, auth_context, tenant_id):
        self.requirement_calls.append((user_id, auth_context, tenant_id))
        return {
            "user_id": user_id,
            "risk_score": 0.4,
            "risk_level": "medium",
            "risk_factors": {},
            "required_factors": ["password", "device_fingerprint"],
            "policies": {},
            "calculated_at": datetime.now(timezone.utc),
        }

    async def verify_adaptive_auth(self, user_id, provided_factors, auth_context, tenant_id):
        self.verify_calls.append((user_id, provided_factors, auth_context, tenant_id))
        return {
            "verified": True,
            "risk_score": 0.2,
            "risk_level": "low",
            "factor_results": [],
            "required_factors": ["password"],
            "missing_factors": [],
            "verified_at": datetime.now(timezone.utc),
        }


@pytest.fixture
def request_context():
    return RequestContext(
        tenant_id=uuid4(),
        user_id=str(uuid4()),
    )


@pytest.fixture
def mfa_test_app(request_context):
    app = FastAPI()
    app.include_router(mfa.router)
    app.dependency_overrides[get_current_request_context] = lambda: request_context
    return app


@pytest.fixture
def mfa_client(mfa_test_app):
    return TestClient(mfa_test_app)


def _override_dependency(app, dependency, value):
    app.dependency_overrides[dependency] = lambda: value


def test_enroll_biometric_rejects_foreign_body_tenant(
    mfa_test_app,
    mfa_client,
):
    biometric_service = BiometricServiceSpy()
    _override_dependency(mfa_test_app, mfa.get_biometric_service, biometric_service)

    response = mfa_client.post(
        "/internal/iam/mfa/biometrics/enroll",
        headers={"authorization": "Bearer test-token"},
        json={
            "user_id": "user-1",
            "biometric_type": "device_fingerprint",
            "enrollment_data": {"samples": []},
            "tenant_id": str(uuid4()),
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert biometric_service.enroll_calls == []


def test_verify_biometric_rejects_foreign_body_tenant(
    mfa_test_app,
    mfa_client,
):
    biometric_service = BiometricServiceSpy()
    _override_dependency(mfa_test_app, mfa.get_biometric_service, biometric_service)

    response = mfa_client.post(
        "/internal/iam/mfa/biometrics/verify",
        headers={"authorization": "Bearer test-token"},
        json={
            "user_id": "user-1",
            "biometric_type": "device_fingerprint",
            "verification_data": {"sample": "x"},
            "tenant_id": str(uuid4()),
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert biometric_service.verify_calls == []


def test_get_user_biometrics_defaults_to_authenticated_tenant(
    mfa_test_app,
    mfa_client,
    request_context,
):
    biometric_service = BiometricServiceSpy()
    _override_dependency(mfa_test_app, mfa.get_biometric_service, biometric_service)

    response = mfa_client.get(
        "/internal/iam/mfa/biometrics/user-1",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert biometric_service.get_calls == [("user-1", str(request_context.tenant_id))]
    assert response.json()["tenant_id"] == str(request_context.tenant_id)


def test_delete_biometric_rejects_foreign_query_tenant(
    mfa_test_app,
    mfa_client,
):
    biometric_service = BiometricServiceSpy()
    _override_dependency(mfa_test_app, mfa.get_biometric_service, biometric_service)

    response = mfa_client.delete(
        f"/internal/iam/mfa/biometrics/user-1/device_fingerprint?tenant_id={uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert biometric_service.delete_calls == []


def test_calculate_auth_risk_rejects_foreign_body_tenant(
    mfa_test_app,
    mfa_client,
):
    adaptive_service = AdaptiveAuthServiceSpy()
    _override_dependency(mfa_test_app, mfa.get_adaptive_auth_service, adaptive_service)

    response = mfa_client.post(
        "/internal/iam/mfa/adaptive/calculate-risk",
        headers={"authorization": "Bearer test-token"},
        json={
            "user_id": "user-1",
            "auth_context": {},
            "tenant_id": str(uuid4()),
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert adaptive_service.risk_calls == []


def test_get_auth_requirements_rejects_foreign_body_tenant(
    mfa_test_app,
    mfa_client,
):
    adaptive_service = AdaptiveAuthServiceSpy()
    _override_dependency(mfa_test_app, mfa.get_adaptive_auth_service, adaptive_service)

    response = mfa_client.post(
        "/internal/iam/mfa/adaptive/requirements",
        headers={"authorization": "Bearer test-token"},
        json={
            "user_id": "user-1",
            "auth_context": {},
            "tenant_id": str(uuid4()),
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert adaptive_service.requirement_calls == []


def test_verify_adaptive_auth_rejects_foreign_body_tenant(
    mfa_test_app,
    mfa_client,
):
    adaptive_service = AdaptiveAuthServiceSpy()
    _override_dependency(mfa_test_app, mfa.get_adaptive_auth_service, adaptive_service)

    response = mfa_client.post(
        "/internal/iam/mfa/adaptive/verify",
        headers={"authorization": "Bearer test-token"},
        json={
            "user_id": "user-1",
            "provided_factors": [],
            "auth_context": {},
            "tenant_id": str(uuid4()),
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert adaptive_service.verify_calls == []
