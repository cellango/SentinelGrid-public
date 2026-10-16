from app.api import routes_posture


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise routes_posture.httpx.HTTPStatusError(
                "upstream error",
                request=None,
                response=self,
            )


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


def test_posture_dashboard_snapshot_proxies_real_cloud_posture(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        routes_posture.httpx,
        "AsyncClient",
        lambda *a, **k: FakeAsyncClient(
            calls,
            {
                "cloud_posture": {
                    "cloud_accounts_connected": 3,
                    "critical_misconfigs": 2,
                    "high_misconfigs": 4,
                    "medium_misconfigs": 6,
                    "low_misconfigs": 8,
                    "total_issues": 20,
                    "biggest_risk": {
                        "title": "Public S3 bucket",
                        "description": "Bucket allows anonymous access",
                        "severity": "critical",
                    },
                    "posture_score": 71,
                }
            },
        ),
    )
    monkeypatch.setattr(routes_posture.settings, "INTERNAL_SERVICE_TOKEN", "internal-test-token", raising=False)

    response = client.get("/api/v1/posture/dashboard-snapshot")

    assert response.status_code == 200
    assert response.json()["cloud_accounts_connected"] == 3
    assert response.json()["critical_misconfigs"] == 2
    assert response.json()["posture_score"] == 71
    assert calls[0]["url"].endswith("/api/v1/orchestrator/tenant/tenant-123/dashboard-snapshot")
    assert calls[0]["headers"]["X-Tenant-ID"] == "tenant-123"
    assert calls[0]["headers"]["Authorization"] == "Bearer internal-test-token"
    assert "X-Request-ID" in calls[0]["headers"]
    assert "X-Correlation-ID" in calls[0]["headers"]


def test_posture_dashboard_snapshot_fails_closed_when_cloud_posture_missing(client, monkeypatch):
    monkeypatch.setattr(
        routes_posture.httpx,
        "AsyncClient",
        lambda *a, **k: FakeAsyncClient([], {"summary": {"ok": True}}),
    )

    response = client.get("/api/v1/posture/dashboard-snapshot")

    assert response.status_code == 503
    assert response.json()["detail"] == "Cloud posture snapshot is unavailable from orchestrator"
