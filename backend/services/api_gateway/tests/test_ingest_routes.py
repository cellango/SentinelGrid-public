from app.api import routes_ingest


class FakeResponse:
    def __init__(self, payload, status_code=200, text=""):
        self._payload = payload
        self.status_code = status_code
        self.text = text or str(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.text)


class FakeAsyncClient:
    def __init__(self, calls, payload):
        self.calls = calls
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def post(self, path, json=None):
        self.calls.append({"path": path, "json": json})
        return FakeResponse(self.payload)


def test_test_pipeline_simulates_shared_pipeline_event(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        routes_ingest,
        "_http_client",
        lambda: FakeAsyncClient(
            calls,
            {
                "docs": [
                    {
                        "doc": {
                            "_source": {
                                "message": "normalized event",
                                "tags": ["shared-diagnostic"],
                            }
                        }
                    }
                ]
            },
        ),
    )

    response = client.post(
        "/api/v1/ingest/test-pipeline",
        json={
            "pipeline": "sentinelgrid-normalize",
            "event": {"message": "raw event", "source": "demo"},
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "normalized event",
        "tags": ["shared-diagnostic"],
    }
    assert calls == [
        {
            "path": "/_ingest/pipeline/sentinelgrid-normalize/_simulate",
            "json": {"docs": [{"_source": {"message": "raw event", "source": "demo"}}]},
        }
    ]


def test_test_pipeline_requires_pipeline_and_event(client):
    response = client.post("/api/v1/ingest/test-pipeline", json={"pipeline": "sentinelgrid-normalize"})

    assert response.status_code == 400
    assert response.json()["detail"] == "pipeline and event are required"
