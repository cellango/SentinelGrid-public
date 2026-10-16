import httpx

from app.api import routes_auth


def test_login_proxy_forwards_tenant_and_realm_headers(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
    tenant_header_matrix,
):
    calls = proxy_async_client_factory(
        routes_auth,
        responses=[proxy_response_factory(payload={"access_token": "token-123"})],
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@example.com", "password": "DemoPassword123!"},
        headers=tenant_header_matrix,
    )

    assert response.status_code == 200
    assert response.json() == {"access_token": "token-123"}
    assert calls[0]["headers"]["x-tenant-id"] == "tenant-123"
    assert calls[0]["headers"]["x-realm"] == "realm-123"
    assert calls[0]["json"] == {
        "email": "analyst@example.com",
        "password": "DemoPassword123!",
    }


def test_refresh_proxy_forwards_tenant_and_realm_headers(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
    tenant_header_matrix,
):
    calls = proxy_async_client_factory(
        routes_auth,
        responses=[proxy_response_factory(payload={"access_token": "token-456"})],
    )

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "refresh-123"},
        headers=tenant_header_matrix,
    )

    assert response.status_code == 200
    assert response.json() == {"access_token": "token-456"}
    assert calls[0]["headers"]["x-tenant-id"] == "tenant-123"
    assert calls[0]["headers"]["x-realm"] == "realm-123"
    assert calls[0]["json"] == {"refresh_token": "refresh-123"}


def test_login_proxy_only_forwards_allowlisted_pre_auth_hints(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
):
    calls = proxy_async_client_factory(
        routes_auth,
        responses=[proxy_response_factory(payload={"access_token": "token-123"})],
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@example.com", "password": "DemoPassword123!"},
        headers={
            "x-tenant-id": "tenant-123",
            "x-realm": "realm-123",
            "authorization": "Bearer should-not-forward",
            "x-extra-header": "drop-me",
        },
    )

    assert response.status_code == 200
    assert calls[0]["headers"] == {
        "Content-Type": "application/json",
        "x-tenant-id": "tenant-123",
        "x-realm": "realm-123",
    }


def test_refresh_proxy_only_forwards_allowlisted_pre_auth_hints(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
):
    calls = proxy_async_client_factory(
        routes_auth,
        responses=[proxy_response_factory(payload={"access_token": "token-456"})],
    )

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "refresh-123"},
        headers={
            "x-tenant-id": "tenant-123",
            "x-realm": "realm-123",
            "authorization": "Bearer should-not-forward",
            "x-extra-header": "drop-me",
        },
    )

    assert response.status_code == 200
    assert calls[0]["headers"] == {
        "Content-Type": "application/json",
        "x-tenant-id": "tenant-123",
        "x-realm": "realm-123",
    }


def test_login_proxy_returns_upstream_error_payload_and_status(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
):
    proxy_async_client_factory(
        routes_auth,
        responses=[
            proxy_response_factory(
                status_code=401,
                payload={"detail": "Invalid credentials"},
            )
        ],
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


def test_refresh_proxy_returns_upstream_error_payload_and_status(
    client,
    proxy_async_client_factory,
    proxy_response_factory,
):
    proxy_async_client_factory(
        routes_auth,
        responses=[
            proxy_response_factory(
                status_code=403,
                payload={"detail": "Refresh token expired"},
            )
        ],
    )

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "expired-refresh"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Refresh token expired"}


def test_login_proxy_returns_503_when_iam_is_unreachable(
    client,
    proxy_async_client_factory,
):
    proxy_async_client_factory(
        routes_auth,
        exception=httpx.ConnectError("IAM unavailable"),
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@example.com", "password": "DemoPassword123!"},
    )

    assert response.status_code == 503
    assert "IAM login proxy failed" in response.json()["detail"]


def test_refresh_proxy_returns_503_when_iam_is_unreachable(
    client,
    proxy_async_client_factory,
):
    proxy_async_client_factory(
        routes_auth,
        exception=httpx.ConnectError("IAM unavailable"),
    )

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "refresh-123"},
    )

    assert response.status_code == 503
    assert "IAM refresh proxy failed" in response.json()["detail"]
