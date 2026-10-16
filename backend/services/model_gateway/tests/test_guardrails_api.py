import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app.main import app
from app.api import embeddings as embeddings_api
from app.core.database import get_db, get_tenant_session


class FakeEmbedder:
    def generate_embedding(self, text):
        return [0.1] * 384


class FakeDB:
    def __init__(self):
        self.records = []
        # Provide a minimal bind with dialect name so ingest code can skip complex paths
        class _Dial:
            name = "sqlite"
        class _Bind:
            dialect = _Dial()
        self._bind = _Bind()
        self._query_store = []

    def add(self, obj):
        self.records.append(obj)

    def flush(self):
        return

    def commit(self):
        return

    def rollback(self):
        return

    def get_bind(self):
        return self._bind

    def close(self):
        return

    def execute(self, *args, **kwargs):
        # Return an object with .mappings() yielding empty list for searches
        class _Empty:
            def mappings(self_inner):
                return []

        return _Empty()

    class _Query:
        def __init__(self, outer, model):
            self.outer = outer
            self.model = model
            self.filters = {}

        def filter_by(self, **kwargs):
            self.filters.update(kwargs)
            return self

        def one_or_none(self):
            for rec in self.outer.records:
                if all(getattr(rec, k, None) == v for k, v in self.filters.items()):
                    return rec
            return None

    def query(self, model):
        return self._Query(self, model)


@pytest.fixture
def client_with_overrides():
    fake_db = FakeDB()

    def override_db():
        yield fake_db

    def override_tenant_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_session] = override_tenant_db
    app.dependency_overrides[embeddings_api.get_embedding_service] = lambda: FakeEmbedder()
    embeddings_api._embedding_service = FakeEmbedder()
    client = TestClient(app, raise_server_exceptions=False)
    yield client, fake_db
    app.dependency_overrides.clear()
    embeddings_api._embedding_service = None


def test_embedding_ingest_redacts_secrets(client_with_overrides):
    client, fake_db = client_with_overrides
    payload = {
        "summaries": [
            {
                "tenant_id": "11111111-1111-1111-1111-111111111111",
                "source": "test",
                "agent_id": None,
                "host_id": None,
                "os_id": "os-1",
                "timestamp": datetime.utcnow().isoformat(),
                "summary": "api_key=SECRET1234567890 password=something user test@example.com",
                "fields": {"token": "password=supersecret"},
            }
        ]
    }
    resp = client.post("/api/v1/embeddings/security-events", json=payload, headers={"X-Tenant-ID": payload["summaries"][0]["tenant_id"]})
    assert resp.status_code == 200
    assert fake_db.records, "Expected a record to be added to the DB session"
    stored = fake_db.records[0]
    assert "SECRET" not in stored.summary
    assert "supersecret" not in str(stored.fields)
    assert "[REDACTED]" in stored.summary


def test_chat_requires_tenant_header(client_with_overrides):
    client, _ = client_with_overrides
    resp = client.post("/api/v1/chat/vuln", json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "help"})
    assert resp.status_code == 400
    resp_ok = client.post(
        "/api/v1/chat/vuln",
        json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "help"},
        headers={"X-Tenant-ID": "11111111-1111-1111-1111-111111111111"},
    )
    assert resp_ok.status_code == 200
