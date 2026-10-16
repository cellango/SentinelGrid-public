"""Focused tenant-isolation coverage for embeddings and RAG routes."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import embeddings as embeddings_api
from app.core.database import get_db, get_tenant_session
from app.main import app


class _FakeDB:
    def __init__(self):
        self.records = []

        class _Dial:
            name = "sqlite"

        class _Bind:
            dialect = _Dial()

        self._bind = _Bind()

    def add(self, obj):
        self.records.append(obj)

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None

    def get_bind(self):
        return self._bind

    def execute(self, *args, **kwargs):
        class _Result:
            def __init__(self, scalar_value=0, mappings_rows=None):
                self._scalar_value = scalar_value
                self._mappings_rows = mappings_rows or []

            def scalar(self):
                return self._scalar_value

            def mappings(self):
                return self._mappings_rows

        return _Result()

    class _Query:
        def __init__(self, outer):
            self.outer = outer
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
        return self._Query(self)


class _FakeEmbedder:
    def generate_embedding(self, text):
        return [0.1] * 384


def _unexpected_dependency():
    raise AssertionError("Unexpected DB dependency used")
    yield  # pragma: no cover


@pytest.fixture
def client_with_tenant_session():
    fake_db = _FakeDB()

    def override_tenant_db():
        yield fake_db

    app.dependency_overrides[get_db] = _unexpected_dependency
    app.dependency_overrides[get_tenant_session] = override_tenant_db
    app.dependency_overrides[embeddings_api.get_embedding_service] = lambda: _FakeEmbedder()
    embeddings_api._embedding_service = _FakeEmbedder()
    client = TestClient(app, raise_server_exceptions=False)
    try:
        yield client, fake_db
    finally:
        app.dependency_overrides.clear()
        embeddings_api._embedding_service = None


def test_embeddings_health_uses_tenant_session(client_with_tenant_session):
    client, _ = client_with_tenant_session

    response = client.get("/api/v1/embeddings/health", headers={"X-Tenant-ID": str(uuid4())})

    assert response.status_code == 200
    assert "status" in response.json()


def test_embedding_ingest_rejects_cross_tenant_summary(client_with_tenant_session):
    client, fake_db = client_with_tenant_session
    header_tenant = str(uuid4())
    body_tenant = str(uuid4())

    response = client.post(
        "/api/v1/embeddings/security-events",
        headers={"X-Tenant-ID": header_tenant},
        json={
            "summaries": [
                {
                    "tenant_id": body_tenant,
                    "source": "test",
                    "agent_id": None,
                    "host_id": None,
                    "os_id": "os-1",
                    "timestamp": datetime.utcnow().isoformat(),
                    "summary": "example",
                    "fields": {},
                }
            ]
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"
    assert fake_db.records == []


def test_embedding_search_rejects_cross_tenant_payload(client_with_tenant_session):
    client, _ = client_with_tenant_session
    header_tenant = str(uuid4())
    body_tenant = str(uuid4())

    response = client.post(
        "/api/v1/embeddings/security-events/search",
        headers={"X-Tenant-ID": header_tenant},
        json={"tenant_id": body_tenant, "query": "malware", "limit": 5},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"


def test_rag_post_search_defaults_to_authenticated_tenant(client_with_tenant_session):
    client, _ = client_with_tenant_session
    tenant_id = str(uuid4())

    with patch("app.api.rag.RAGService") as service_cls:
        service = MagicMock()
        service.search.return_value = []
        service_cls.return_value = service

        response = client.post(
            "/internal/llm/rag/search",
            headers={"X-Tenant-ID": tenant_id},
            json={"query": "soc2", "top_k": 3},
        )

    assert response.status_code == 200
    assert service.search.call_args.kwargs["tenant_id"] == tenant_id


def test_rag_get_search_rejects_cross_tenant_query(client_with_tenant_session):
    client, _ = client_with_tenant_session
    header_tenant = str(uuid4())
    query_tenant = str(uuid4())

    response = client.get(
        f"/internal/llm/rag/search?query=soc2&tenant_id={query_tenant}",
        headers={"X-Tenant-ID": header_tenant},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"


def test_rag_store_rejects_cross_tenant_body(client_with_tenant_session):
    client, _ = client_with_tenant_session
    header_tenant = str(uuid4())
    body_tenant = str(uuid4())

    response = client.post(
        "/internal/llm/rag/knowledge",
        headers={"X-Tenant-ID": header_tenant},
        json={
            "category": "nist",
            "title": "AC-2",
            "content": "Manage accounts",
            "tenant_id": body_tenant,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Cross-tenant access denied"


def test_rag_store_defaults_to_authenticated_tenant(client_with_tenant_session):
    client, fake_db = client_with_tenant_session
    tenant_id = str(uuid4())

    with patch("app.api.rag.RAGService") as service_cls:
        service = MagicMock()
        service.store_knowledge.return_value = {"status": "success", "id": "kb-1", "category": "nist"}
        service_cls.return_value = service

        response = client.post(
            "/internal/llm/rag/knowledge",
            headers={"X-Tenant-ID": tenant_id},
            json={
                "category": "nist",
                "title": "AC-2",
                "content": "Manage accounts",
            },
        )

    assert response.status_code == 200
    assert fake_db.records == []
    assert service.store_knowledge.call_args.kwargs["tenant_id"] == tenant_id
