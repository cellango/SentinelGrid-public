from fastapi.testclient import TestClient

from tests.constants import TEST_ORG_ID


def test_gateway_config_requires_internal_token(client: TestClient):
    response = client.get(f"/api/v1/gateway/config/{TEST_ORG_ID}")
    assert response.status_code == 403


def test_gateway_config_rejects_cross_tenant_access(
    client: TestClient,
    internal_headers: dict[str, str],
):
    response = client.get(
        f"/api/v1/gateway/config/{TEST_ORG_ID}",
        headers={**internal_headers, "X-Tenant-ID": "33333333-3333-3333-3333-333333333333"},
    )
    assert response.status_code == 403


def test_validate_api_key_returns_server_derived_context(
    db_client: TestClient,
    internal_headers: dict[str, str],
):
    create_response = db_client.post(
        "/api/v1/ai-apps",
        headers=internal_headers,
        json={
            "org_id": TEST_ORG_ID,
            "name": "AuthBoundaryApp",
            "environment": "prod",
        },
    )
    assert create_response.status_code == 200
    api_key = create_response.json()["api_key"]
    app_id = create_response.json()["id"]

    response = db_client.post(
        "/internal/auth/validate-api-key",
        headers={"Authorization": "Bearer internal-service-token-change-in-production"},
        json={"api_key": api_key},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "valid": True,
        "org_id": TEST_ORG_ID,
        "app_id": app_id,
        "realm": "prod",
        "app_name": "AuthBoundaryApp",
    }


def test_validate_api_key_rejects_invalid_key(db_client: TestClient):
    response = db_client.post(
        "/internal/auth/validate-api-key",
        headers={"Authorization": "Bearer internal-service-token-change-in-production"},
        json={"api_key": "sg-ai-invalid"},
    )

    assert response.status_code == 401
