"""Baseline onboarding rule enablement requires an owned mutation contract."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.mark.parametrize(
    "keys",
    [
        ["failed_logins", "new_admin", "suspicious_cloud"],
        ["invalid_rule"],
        ["failed_logins"],
        [],
        ["new_admin"],
    ],
)
def test_enable_rules_is_unavailable_before_ad_hoc_SQL(keys):
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/rules/enable",
            json={
                "tenant_id": "11111111-1111-4111-8111-111111111111",
                "rule_keys": keys,
            },
        )
    assert response.status_code == 503
