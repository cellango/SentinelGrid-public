from app.api import routes_iam


def test_dashboard_snapshot_forwards_authenticated_tenant_and_authorization(client, proxy_async_client_factory, proxy_response_factory):
    calls = proxy_async_client_factory(routes_iam, responses=[proxy_response_factory(payload={"summary": {"users": 7}})])
    response = client.get("/api/v1/iam/dashboard-snapshot", headers={
        "x-request-id": "req-123", "x-correlation-id": "corr-123", "x-tenant-id": "foreign-tenant",
        "authorization": "Bearer gateway-token"})
    assert response.status_code == 200 and response.json() == {"summary": {"users": 7}}
    assert calls[0]["url"].endswith("/api/v1/iam/dashboard-snapshot")
    assert calls[0]["headers"]["x-tenant-id"] == "tenant-123"
    assert calls[0]["headers"]["authorization"] == "Bearer gateway-token"
    assert calls[0]["headers"]["X-Request-ID"] == "req-123"
    assert calls[0]["headers"]["X-Correlation-ID"] == "corr-123"


def test_dashboard_snapshot_rejects_missing_authorization_without_service_token_fallback(client, proxy_async_client_factory, monkeypatch):
    calls = proxy_async_client_factory(routes_iam)
    monkeypatch.setattr(routes_iam.settings, "INTERNAL_SERVICE_TOKEN", "internal-test-token")
    assert client.get("/api/v1/iam/dashboard-snapshot").status_code == 401
    assert calls == []
