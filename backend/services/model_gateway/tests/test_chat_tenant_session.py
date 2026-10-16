"""Focused tenant-session coverage for vuln chat."""

from fastapi.testclient import TestClient

from app.api import chat as chat_api
from app.api import embeddings as embeddings_api
from app.main import app
from app.core.database import get_db, get_tenant_session


class _FakeDB:
    def execute(self, *args, **kwargs):
        class _Empty:
            def mappings(self_inner):
                return []

        return _Empty()


class _FakeEmbedder:
    def generate_embedding(self, text):
        return [0.1] * 384


def _unexpected_dependency():
    raise AssertionError("Unexpected plain DB dependency used")
    yield  # pragma: no cover


def test_vuln_chat_uses_tenant_session():
    fake_db = _FakeDB()

    def override_tenant_db():
        yield fake_db

    app.dependency_overrides[get_db] = _unexpected_dependency
    app.dependency_overrides[get_tenant_session] = override_tenant_db
    app.dependency_overrides[embeddings_api.get_embedding_service] = lambda: _FakeEmbedder()
    embeddings_api._embedding_service = _FakeEmbedder()

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/v1/chat/vuln",
            json={"tenant_id": "11111111-1111-1111-1111-111111111111", "query": "help"},
            headers={"X-Tenant-ID": "11111111-1111-1111-1111-111111111111"},
        )
    finally:
        app.dependency_overrides.clear()
        embeddings_api._embedding_service = None

    assert response.status_code == 200


def test_vuln_chat_rejects_cross_tenant_payload():
    fake_db = _FakeDB()

    def override_tenant_db():
        yield fake_db

    app.dependency_overrides[get_db] = _unexpected_dependency
    app.dependency_overrides[get_tenant_session] = override_tenant_db
    app.dependency_overrides[embeddings_api.get_embedding_service] = lambda: _FakeEmbedder()
    embeddings_api._embedding_service = _FakeEmbedder()

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/v1/chat/vuln",
            json={"tenant_id": "22222222-2222-2222-2222-222222222222", "query": "help"},
            headers={"X-Tenant-ID": "11111111-1111-1111-1111-111111111111"},
        )
    finally:
        app.dependency_overrides.clear()
        embeddings_api._embedding_service = None

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"
