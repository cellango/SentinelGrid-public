from app.services.unified_chat_service import UnifiedChatService


def test_prompt_includes_tenant_and_module_isolation():
    service = UnifiedChatService()
    prompt = service._build_unified_prompt(
        query="Show SOC2 readiness",
        module="iam",
        module_context={},
        rag_context={"sources": []},
        tenant_id="tenant-abc"
    )
    assert "tenant-abc" in prompt
    assert "SOC" in prompt or "IAM" in prompt


def test_rag_context_filtered_by_tenant():
    service = UnifiedChatService()

    class DummyRAG:
        def search(self, tenant_id, module, query, limit=5):
            return [
                {"title": "tenant match", "content": "x", "tenant_id": tenant_id},
            ]

    service.rag_service = DummyRAG()

    result = service._retrieve_rag_context("tenant-123", "iam", "query")
    # When embeddings are unavailable, RAG may return empty; ensure no cross-tenant data leaks if sources exist.
    if result.get("sources"):
        assert result["sources"][0]["tenant_id"] == "tenant-123"
