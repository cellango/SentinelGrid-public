"""
Unit tests for Unified Chat Service
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services.unified_chat_service import UnifiedChatService


class TestUnifiedChatService:
    """Test suite for UnifiedChatService."""
    
    def test_init(self):
        """Test service initialization."""
        service = UnifiedChatService()
        
        assert service.module_keywords is not None
        assert "iam" in service.module_keywords
        assert "soc" in service.module_keywords
        assert "siem" in service.module_keywords
    
    def test_detect_module_from_context_incident(self):
        """Test module detection from context (SOC incident)."""
        service = UnifiedChatService()
        
        context = {"current_incident_id": "inc-123"}
        module = service._detect_module("What should I do?", context)
        
        assert module == "soc"
    
    def test_detect_module_from_context_policy(self):
        """Test module detection from context (IAM policy)."""
        service = UnifiedChatService()
        
        context = {"current_policy_id": "policy-123"}
        module = service._detect_module("How does this work?", context)
        
        assert module == "iam"
    
    def test_detect_module_from_context_log_query(self):
        """Test module detection from context (SIEM log query)."""
        service = UnifiedChatService()
        
        context = {"log_query": "SELECT * FROM logs"}
        module = service._detect_module("Analyze this", context)
        
        assert module == "siem"

    def test_detect_module_from_active_compliance_agent(self):
        """Test module detection from active Compliance Agent context."""
        service = UnifiedChatService()

        context = {"dashboard_data": {"active_agent": "compliance_agent"}}
        module = service._detect_module("/compliance status", context)

        assert module == "compliance"
    
    def test_detect_module_from_keywords_iam(self):
        """Test module detection from IAM keywords."""
        service = UnifiedChatService()
        
        module = service._detect_module("What roles does this user have?", None)
        
        assert module == "iam"
    
    def test_detect_module_from_keywords_soc(self):
        """Test module detection from SOC keywords."""
        service = UnifiedChatService()
        
        module = service._detect_module("How do I respond to this malware incident?", None)
        
        assert module == "soc"
    
    def test_detect_module_from_keywords_siem(self):
        """Test module detection from SIEM keywords."""
        service = UnifiedChatService()
        
        module = service._detect_module("Search for failed login events in the logs", None)
        
        assert module == "siem"

    def test_detect_module_from_compliance_keywords(self):
        """Test module detection from compliance keywords."""
        service = UnifiedChatService()

        module = service._detect_module("Which SOC 2 controls have evidence gaps?", None)

        assert module == "compliance"
    
    def test_detect_module_no_signal(self):
        """Test module detection when no clear signal."""
        service = UnifiedChatService()
        
        module = service._detect_module("Hello", None)
        
        # Should default to "general" when no keywords match
        assert module == "general"
    
    def test_detect_module_multiple_keywords(self):
        """Test module detection with multiple keywords (should pick highest score)."""
        service = UnifiedChatService()
        
        # Query with both IAM and SOC keywords, but more SOC
        module = service._detect_module("How do I respond to this alert about user access incidents?", None)
        
        # SOC should win (incident, alert, response)
        assert module == "soc"
    
    def test_process_chat_query_with_explicit_module(self):
        """Test processing query with explicitly specified module."""
        service = UnifiedChatService()
        
        with patch.object(service, '_get_module_context') as mock_context, \
             patch.object(service, '_retrieve_rag_context') as mock_rag, \
             patch.object(service, '_build_unified_prompt') as mock_prompt:
            
            mock_context.return_value = {"users": 10}
            mock_rag.return_value = {"sources": []}
            mock_prompt.return_value = "Full prompt"
            
            result = service.process_chat_query(
                query="Test query",
                tenant_id="tenant-123",
                module="iam"
            )
            
            assert result["module"] == "iam"
            assert result["tenant_id"] == "tenant-123"
            assert "prompt" in result
            mock_context.assert_called_once_with("tenant-123", "iam", None)
    
    def test_process_chat_query_auto_detect_module(self):
        """Test processing query with auto-detected module."""
        service = UnifiedChatService()
        
        with patch.object(service, '_detect_module', return_value="soc") as mock_detect, \
             patch.object(service, '_get_module_context') as mock_context, \
             patch.object(service, '_retrieve_rag_context') as mock_rag, \
             patch.object(service, '_build_unified_prompt') as mock_prompt:
            
            mock_context.return_value = {}
            mock_rag.return_value = {"sources": []}
            mock_prompt.return_value = "Prompt"
            
            result = service.process_chat_query(
                query="How do I handle this incident?",
                tenant_id="tenant-123"
            )
            
            assert result["module"] == "soc"
            mock_detect.assert_called_once()
    
    def test_process_chat_query_includes_sources(self):
        """Test that RAG sources are included in response."""
        service = UnifiedChatService()
        
        with patch.object(service, '_get_module_context'), \
             patch.object(service, '_retrieve_rag_context') as mock_rag, \
             patch.object(service, '_build_unified_prompt'):
            
            mock_rag.return_value = {
                "sources": [
                    {"title": "NIST AC-2", "similarity": 0.9},
                    {"title": "MITRE T1078", "similarity": 0.85}
                ]
            }
            
            result = service.process_chat_query(
                query="Test",
                tenant_id="tenant-123",
                module="iam"
            )
            
            assert "sources" in result
            assert len(result["sources"]) == 2
    
    def test_get_module_context_iam(self):
        """Test getting IAM module context."""
        service = UnifiedChatService()
        
        with patch('app.services.unified_chat_service.ModelService') as mock_model:
            # Mock would typically fetch from IAM service
            context = service._get_module_context("tenant-123", "iam", None)
            
            # Should return dict (implementation specific)
            assert isinstance(context, dict)
    
    def test_get_module_context_soc(self):
        """Test getting SOC module context."""
        service = UnifiedChatService()
        
        context = service._get_module_context("tenant-123", "soc", None)
        
        assert isinstance(context, dict)
    
    def test_get_module_context_siem(self):
        """Test getting SIEM module context."""
        service = UnifiedChatService()
        
        context = service._get_module_context("tenant-123", "siem", None)
        
        assert isinstance(context, dict)
    
    @patch('app.services.unified_chat_service.RAGService')
    def test_retrieve_rag_context(self, mock_rag_class):
        """Test RAG context retrieval."""
        service = UnifiedChatService()
        
        mock_rag = Mock()
        mock_rag.search.return_value = [
            {"title": "AC-2", "content": "Account Management", "similarity": 0.9}
        ]
        mock_rag_class.return_value = mock_rag
        
        # Need to set up RAG service if not already initialized
        service.rag_service = mock_rag
        
        result = service._retrieve_rag_context("tenant-123", "iam", "user roles")
        
        assert "sources" in result or isinstance(result, dict)
        assert mock_rag.search.call_count == 2
    
    def test_build_unified_prompt_iam(self):
        """Test building unified prompt for IAM module."""
        service = UnifiedChatService()
        
        prompt = service._build_unified_prompt(
            query="What roles does user have?",
            module="iam",
            module_context={"users": 10, "roles": 5},
            rag_context={"sources": []},
            tenant_id="tenant-123"
        )
        
        assert isinstance(prompt, str)
        assert "user" in prompt.lower() or "iam" in prompt.lower()
    
    def test_build_unified_prompt_soc(self):
        """Test building unified prompt for SOC module."""
        service = UnifiedChatService()
        
        prompt = service._build_unified_prompt(
            query="How do I respond?",
            module="soc",
            module_context={"active_incidents": 2},
            rag_context={"sources": []},
            tenant_id="tenant-123"
        )
        
        assert isinstance(prompt, str)
        assert "tenant-123" in prompt

    def test_build_unified_prompt_includes_rag_sources(self):
        """Test that RAG sources are included in prompt."""
        service = UnifiedChatService()
        
        rag_context = {
            "sources": [
                {
                    "title": "NIST AC-2",
                    "content": "Account Management control",
                    "similarity": 0.9
                }
            ]
        }
        
        prompt = service._build_unified_prompt(
            query="What is AC-2?",
            module="iam",
            module_context={},
            rag_context=rag_context,
            tenant_id="tenant-123"
        )
        
        assert isinstance(prompt, str)
        # Prompt should include RAG context
        assert "AC-2" in prompt or "Account Management" in prompt
    
    def test_process_chat_query_with_context(self):
        """Test processing query with additional context."""
        service = UnifiedChatService()
        
        context = {
            "current_incident_id": "inc-123",
            "user_id": "user-456"
        }
        
        with patch.object(service, '_get_module_context') as mock_context, \
             patch.object(service, '_retrieve_rag_context') as mock_rag, \
             patch.object(service, '_build_unified_prompt'):
            
            mock_context.return_value = {}
            mock_rag.return_value = {"sources": []}
            
            result = service.process_chat_query(
                query="Test",
                tenant_id="tenant-123",
                module=None,  # Auto-detect
                context=context
            )
            
            # Should detect SOC from incident context
            assert result["module"] == "soc"
            mock_context.assert_called_once_with("tenant-123", "soc", context)
    
    def test_module_keywords_coverage(self):
        """Test that module keywords cover common use cases."""
        service = UnifiedChatService()
        
        # Verify IAM keywords
        assert "user" in service.module_keywords["iam"]
        assert "role" in service.module_keywords["iam"]
        assert "permission" in service.module_keywords["iam"]
        assert "policy" in service.module_keywords["iam"]
        
        # Verify SOC keywords
        assert "incident" in service.module_keywords["soc"]
        assert "playbook" in service.module_keywords["soc"]
        assert "alert" in service.module_keywords["soc"]
        assert "threat" in service.module_keywords["soc"]
        
        # Verify SIEM keywords
        assert "log" in service.module_keywords["siem"]
        assert "event" in service.module_keywords["siem"]
        assert "query" in service.module_keywords["siem"]
        assert "detection" in service.module_keywords["siem"]

        # Verify compliance keywords
        assert "compliance" in service.module_keywords["compliance"]
        assert "evidence" in service.module_keywords["compliance"]
        assert "gap" in service.module_keywords["compliance"]

    def test_compliance_context_marks_live_status_and_actions(self):
        """Test compliance live context provenance and proposed actions."""
        service = UnifiedChatService()
        context = {
            "active_agent": "compliance_agent",
            "compliance_live_context": {
                "retrieval_categories": ["reports", "controls", "evidence", "gaps"],
                "coverage": {"status": "available", "high_priority_gap_count": 1},
                "recommendations": {
                    "status": "available",
                    "items": [
                        {
                            "id": "rec-1",
                            "title": "Collect MFA evidence",
                            "recommendation_type": "create_evidence_collection_task",
                        }
                    ],
                },
            },
        }

        with patch.object(service, '_retrieve_rag_context', return_value={"sources": []}):
            result = service.process_chat_query(
                query="/compliance status",
                tenant_id="tenant-123",
                context=context,
            )

        assert result["module"] == "compliance"
        assert result["source_kind"] == "proposed_agent_action"
        assert result["retrieval_categories"] == ["reports", "controls", "evidence", "gaps"]
        assert result["actions"][0]["recommendation_id"] == "rec-1"
    
    def test_process_chat_query_returns_timestamp(self):
        """Test that response includes timestamp."""
        service = UnifiedChatService()
        
        with patch.object(service, '_get_module_context'), \
             patch.object(service, '_retrieve_rag_context'), \
             patch.object(service, '_build_unified_prompt'):
            
            result = service.process_chat_query(
                query="Test",
                tenant_id="tenant-123",
                module="iam"
            )
            
            assert "generated_at" in result
            assert isinstance(result["generated_at"], str)
    
    def test_process_chat_query_returns_confidence(self):
        """Test that response includes confidence score."""
        service = UnifiedChatService()
        
        with patch.object(service, '_get_module_context'), \
             patch.object(service, '_retrieve_rag_context'), \
             patch.object(service, '_build_unified_prompt'):
            
            result = service.process_chat_query(
                query="Test",
                tenant_id="tenant-123",
                module="iam"
            )
            
            assert "confidence" in result
            assert isinstance(result["confidence"], (int, float))
