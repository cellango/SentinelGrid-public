from app.api import routes_iam


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.text)


class FakeAsyncClient:
    def __init__(self, recorder, payload):
        self.recorder = recorder
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def get(self, url, headers=None):
        self.recorder.append(
            {
                "url": url,
                "headers": headers or {},
            }
        )
        return FakeResponse(self.payload)


def test_dashboard_snapshot_forwards_authenticated_tenant_and_authorization(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        routes_iam.httpx,
        "AsyncClient",
        lambda *a, **k: FakeAsyncClient(calls, {"summary": {"users": 7}}),
    )

    response = client.get(
        "/api/v1/iam/dashboard-snapshot",
        headers={
            "x-request-id": "req-123",
            "x-correlation-id": "corr-123",
            "x-tenant-id": "foreign-tenant",
            "authorization": "Bearer gateway-token",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"summary": {"users": 7}}
    assert calls[0]["url"].endswith("/api/v1/iam/dashboard-snapshot")
    assert calls[0]["headers"]["X-Tenant-ID"] == "tenant-123"
    assert calls[0]["headers"]["Authorization"] == "Bearer gateway-token"
    assert calls[0]["headers"]["X-Request-ID"] == "req-123"
    assert calls[0]["headers"]["X-Correlation-ID"] == "corr-123"


def test_dashboard_snapshot_uses_internal_token_when_authorization_missing(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        routes_iam.httpx,
        "AsyncClient",
        lambda *a, **k: FakeAsyncClient(calls, {"summary": {"users": 7}}),
    )
    monkeypatch.setattr(routes_iam.settings, "INTERNAL_SERVICE_TOKEN", "internal-test-token", raising=False)

    response = client.get("/api/v1/iam/dashboard-snapshot")

    assert response.status_code == 200
    assert response.json() == {"summary": {"users": 7}}
    assert calls[0]["headers"]["X-Tenant-ID"] == "tenant-123"
    assert calls[0]["headers"]["Authorization"] == "Bearer internal-test-token"
    assert "X-Request-ID" in calls[0]["headers"]
    assert "X-Correlation-ID" in calls[0]["headers"]
