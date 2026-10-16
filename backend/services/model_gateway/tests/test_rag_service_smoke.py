"""RAG service smoke using SQLite fallback (no pgvector)."""

import pytest
from unittest.mock import Mock, patch

from app.services.rag_service import RAGService


class _StubDB:
    def __init__(self):
        self._execute_called = False

    def execute(self, *args, **kwargs):
        self._execute_called = True

        class _Result:
            def mappings(self_inner):
                return self_inner

            def all(self_inner):
                return []

        return _Result()


@patch("app.services.rag_service.EmbeddingsService")
def test_rag_search_returns_list_without_pgvector(mock_embeddings_class):
    # Use a stub DB to ensure call path does not crash without pgvector table
    mock_embeddings = Mock()
    mock_embeddings.generate_embedding.return_value = [0.1] * 1024
    mock_embeddings_class.return_value = mock_embeddings
    db = _StubDB()
    service = RAGService(db_session=db)

    results = service.search("What is AC-2?", tenant_id="tenant-123")
    assert isinstance(results, list)
    # If execute was called, ensure we handled empty results gracefully
    assert db._execute_called


@patch("app.services.rag_service.EmbeddingsService")
def test_store_knowledge_without_db(mock_embeddings_class):
    mock_embeddings_class.return_value = Mock(generate_embedding=Mock(return_value=[0.1] * 1024))
    service = RAGService(db_session=None)
    result = service.store_knowledge(
        category="nist",
        title="AC-2 Account Management",
        content="Manage accounts and review access regularly."
    )
    assert result["status"] == "error"
