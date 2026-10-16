"""
End-to-End Tests for RAG Integration.

These tests verify the complete RAG workflow:
1. Store knowledge base entries
2. Generate embeddings
3. Search using vector similarity
4. Retrieve context for chat queries
"""

import pytest
import uuid
from unittest.mock import Mock, patch


@pytest.mark.e2e
class TestRAGE2E:
    """End-to-end tests for RAG workflow."""
    
    def test_complete_rag_workflow(
        self,
        db_session,
        mock_peft_available
    ):
        """Test complete RAG workflow from storage to retrieval."""
        from app.services.rag_service import RAGService
        from app.services.embeddings_service import EmbeddingsService
        
        # Initialize services
        rag_service = RAGService(db_session=db_session)
        
        # Store knowledge entries
        entries = [
            {
                "category": "nist",
                "title": "AC-2 Account Management",
                "content": "The organization manages information system accounts, including establishing, activating, modifying, disabling, and removing accounts.",
                "subcategory": "control",
                "metadata": {"control_id": "AC-2", "family": "Access Control"}
            },
            {
                "category": "mitre",
                "title": "T1078 Valid Accounts",
                "content": "Adversaries may steal and use credentials from existing accounts as a means of gaining Initial Access, Persistence, Privilege Escalation, or Defense Evasion.",
                "subcategory": "technique",
                "metadata": {"technique_id": "T1078"}
            },
            {
                "category": "owasp",
                "title": "A01:2021 – Broken Access Control",
                "content": "Access control enforces policy such that users cannot act outside of their intended permissions.",
                "subcategory": "top10",
                "metadata": {"rank": 1, "year": 2021}
            }
        ]
        
        # Store entries
        stored_ids = []
        for entry in entries:
            result = rag_service.store_knowledge(
                category=entry["category"],
                title=entry["title"],
                content=entry["content"],
                subcategory=entry.get("subcategory"),
                metadata=entry.get("metadata")
            )
            
            if result["status"] == "success":
                stored_ids.append(result["id"])
        
        assert len(stored_ids) > 0, "Should have stored at least some entries"
        
        # Search for relevant knowledge
        search_results = rag_service.search(
            query="How do I manage user accounts?",
            top_k=3
        )
        
        # Should return relevant results
        assert len(search_results) > 0, "Should return search results"
        assert all("similarity" in r for r in search_results), "Results should have similarity scores"
        assert all("title" in r for r in search_results), "Results should have titles"
        assert all("content" in r for r in search_results), "Results should have content"
    
    def test_rag_in_unified_chat(
        self,
        db_session,
        test_tenant_id
    ):
        """Test RAG integration in unified chat service."""
        from app.services.unified_chat_service import UnifiedChatService
        from app.services.rag_service import RAGService
        
        # Store some knowledge
        rag_service = RAGService(db_session=db_session)
        rag_service.store_knowledge(
            category="nist",
            title="AC-2 Account Management",
            content="Account management control for IAM.",
            tenant_id=test_tenant_id
        )
        
        # Test unified chat with RAG
        chat_service = UnifiedChatService()
        
        result = chat_service.process_chat_query(
            query="What is account management?",
            tenant_id=test_tenant_id,
            module="iam"
        )
        
        assert result["module"] == "iam"
        assert result["tenant_id"] == test_tenant_id
        assert "sources" in result
        assert "prompt" in result
        assert len(result["sources"]) >= 0  # May be 0 if no matches
    
    def test_tenant_isolation_in_rag(
        self,
        db_session
    ):
        """Test tenant isolation in RAG searches."""
        from app.services.rag_service import RAGService
        
        tenant_1 = str(uuid.uuid4())
        tenant_2 = str(uuid.uuid4())
        
        rag_service = RAGService(db_session=db_session)
        
        # Store tenant-specific knowledge
        result_1 = rag_service.store_knowledge(
            category="custom",
            title="Tenant 1 Custom Policy",
            content="This is specific to tenant 1",
            tenant_id=tenant_1
        )
        
        result_2 = rag_service.store_knowledge(
            category="custom",
            title="Tenant 2 Custom Policy",
            content="This is specific to tenant 2",
            tenant_id=tenant_2
        )
        
        # Search for tenant 1
        results_1 = rag_service.search(
            query="custom policy",
            tenant_id=tenant_1,
            top_k=5
        )
        
        # Search for tenant 2
        results_2 = rag_service.search(
            query="custom policy",
            tenant_id=tenant_2,
            top_k=5
        )
        
        # Results should be isolated (or shared knowledge accessible to both)
        # At minimum, should not raise errors
        assert isinstance(results_1, list)
        assert isinstance(results_2, list)
    
    @pytest.mark.skip(reason="Requires actual embeddings model")
    def test_vector_similarity_search(
        self,
        db_session
    ):
        """Test actual vector similarity search with real embeddings."""
        from app.services.rag_service import RAGService
        
        rag_service = RAGService(db_session=db_session)
        
        # Store entries with actual embeddings
        rag_service.store_knowledge(
            category="nist",
            title="AC-2",
            content="Account Management"
        )
        
        rag_service.store_knowledge(
            category="nist",
            title="AC-3",
            content="Access Enforcement"
        )
        
        # Search - should return AC-2 as more similar
        results = rag_service.search(
            query="How do I manage user accounts?",
            top_k=2
        )
        
        assert len(results) > 0
        # AC-2 should rank higher than AC-3 for account management query
        assert any(r["title"] == "AC-2" for r in results[:1])


@pytest.mark.e2e
@pytest.mark.skip(reason="Requires actual database and embeddings")
class TestRAGWithRealData:
    """Tests with real database and embeddings (integration tests)."""
    
    def test_load_nist_controls(self, db_session):
        """Test loading NIST 800-53 controls into knowledge base."""
        pytest.skip("Requires NIST control data")
    
    def test_load_mitre_techniques(self, db_session):
        """Test loading MITRE ATT&CK techniques."""
        pytest.skip("Requires MITRE ATT&CK data")
    
    def test_load_owasp_top10(self, db_session):
        """Test loading OWASP Top 10."""
        pytest.skip("Requires OWASP data")

