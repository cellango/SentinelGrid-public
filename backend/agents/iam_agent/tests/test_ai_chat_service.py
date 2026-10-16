"""
Unit tests for IAM AI Chat Service
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services.ai_chat_service import IAMChatService
from app.services.keycloak_client import KeycloakClient


@pytest.fixture
def mock_keycloak_client():
    """Mock Keycloak client."""
    return Mock(spec=KeycloakClient)


@pytest.fixture
def mock_model_provider():
    """Mock model provider."""
    mock = Mock()
    mock.generate.return_value = {
        "text": "Test response",
        "confidence": 0.9
    }
    return mock


@pytest.fixture
def ai_chat_service(mock_keycloak_client, mock_model_provider):
    """Create IAMChatService instance."""
    return IAMChatService(
        keycloak_client=mock_keycloak_client,
        model_provider=mock_model_provider
    )


class TestIAMChatService:
    """Test suite for IAMChatService."""
    
    def test_init(self, mock_keycloak_client):
        """Test service initialization."""
        service = IAMChatService(keycloak_client=mock_keycloak_client)
        
        assert service.keycloak_client == mock_keycloak_client
        assert service.model_provider is not None
    
    def test_classify_intent_access_query(self, ai_chat_service):
        """Test intent classification for access queries."""
        intent = ai_chat_service._classify_intent("Who has access to production database?")
        
        assert intent["type"] == "access_query"
        assert intent["action"] == "list_access"
        assert len(intent["entities"]) > 0
        assert any(e["value"] == "production" for e in intent["entities"])
    
    def test_classify_intent_policy_query(self, ai_chat_service):
        """Test intent classification for policy queries."""
        intent = ai_chat_service._classify_intent("What policies are configured?")
        
        assert intent["type"] == "policy_query"
        assert intent["action"] == "list_policies"
    
    def test_classify_intent_role_query(self, ai_chat_service):
        """Test intent classification for role queries."""
        intent = ai_chat_service._classify_intent("What roles exist in the system?")
        
        assert intent["type"] == "role_query"
        assert intent["action"] == "list_roles"
    
    def test_classify_intent_user_query(self, ai_chat_service):
        """Test intent classification for user queries."""
        intent = ai_chat_service._classify_intent("List all users")
        
        assert intent["type"] == "user_query"
        assert intent["action"] == "list_users"
    
    def test_classify_intent_general_query(self, ai_chat_service):
        """Test intent classification for general queries."""
        intent = ai_chat_service._classify_intent("Hello, how are you?")
        
        assert intent["type"] == "general"
    
    def test_gather_iam_data_access_query(self, ai_chat_service):
        """Test gathering IAM data for access queries."""
        intent = {
            "type": "access_query",
            "action": "list_access",
            "entities": [{"type": "resource", "value": "production"}]
        }
        
        mock_roles = [
            {"name": "prod-admin", "users": ["user1", "user2"]}
        ]
        ai_chat_service.keycloak_client.get_realm_roles.return_value = mock_roles
        
        data = ai_chat_service._gather_iam_data(intent, tenant_id="tenant-123")
        
        assert "roles" in data or "access_info" in data
        ai_chat_service.keycloak_client.get_realm_roles.assert_called()
    
    def test_gather_iam_data_policy_query(self, ai_chat_service):
        """Test gathering IAM data for policy queries."""
        intent = {
            "type": "policy_query",
            "action": "list_policies"
        }
        
        # Mock policy retrieval (would call Keycloak or policy service)
        data = ai_chat_service._gather_iam_data(intent, tenant_id="tenant-123")
        
        assert isinstance(data, dict)
    
    def test_build_prompt(self, ai_chat_service):
        """Test prompt building."""
        intent = {
            "type": "access_query",
            "action": "list_access"
        }
        iam_data = {
            "roles": [{"name": "admin"}],
            "users": [{"username": "user1"}]
        }
        
        prompt = ai_chat_service._build_prompt(
            query="Who has access?",
            intent=intent,
            iam_data=iam_data,
            context=None
        )
        
        assert isinstance(prompt, str)
        assert "Who has access?" in prompt
        assert "access_query" in prompt.lower() or "access" in prompt.lower()
    
    def test_build_prompt_with_context(self, ai_chat_service):
        """Test prompt building with additional context."""
        intent = {"type": "general"}
        context = {
            "current_user": "user-123",
            "current_resource": "database-prod"
        }
        
        prompt = ai_chat_service._build_prompt(
            query="Test query",
            intent=intent,
            iam_data={},
            context=context
        )
        
        assert isinstance(prompt, str)
        assert "Test query" in prompt
    
    @patch('app.services.ai_chat_service.httpx')
    def test_query_llm_success(self, mock_httpx, ai_chat_service):
        """Test successful LLM query."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "text": "Response text",
            "confidence": 0.9
        }
        mock_httpx.post.return_value = mock_response
        
        result = ai_chat_service._query_llm("Test prompt")
        
        assert result is not None
        assert "text" in result or isinstance(result, dict)
    
    @patch('app.services.ai_chat_service.httpx')
    def test_query_llm_error(self, mock_httpx, ai_chat_service):
        """Test LLM query error handling."""
        mock_httpx.post.side_effect = Exception("Connection error")
        
        result = ai_chat_service._query_llm("Test prompt")
        
        # Should handle error gracefully
        assert result is not None
    
    def test_parse_response(self, ai_chat_service):
        """Test response parsing."""
        intent = {"type": "access_query"}
        iam_data = {"roles": []}
        llm_response = {
            "text": "User X has admin access",
            "confidence": 0.9
        }
        
        result = ai_chat_service._parse_response(llm_response, intent, iam_data)
        
        assert "answer" in result
        assert result["answer"] == "User X has admin access"
        assert "confidence" in result
    
    def test_chat_success(self, ai_chat_service):
        """Test successful chat query processing."""
        with patch.object(ai_chat_service, '_classify_intent') as mock_intent, \
             patch.object(ai_chat_service, '_gather_iam_data') as mock_gather, \
             patch.object(ai_chat_service, '_build_prompt') as mock_prompt, \
             patch.object(ai_chat_service, '_query_llm') as mock_llm, \
             patch.object(ai_chat_service, '_parse_response') as mock_parse:
            
            mock_intent.return_value = {"type": "general"}
            mock_gather.return_value = {}
            mock_prompt.return_value = "Built prompt"
            mock_llm.return_value = {"text": "Response"}
            mock_parse.return_value = {
                "answer": "Response",
                "confidence": 0.9
            }
            
            result = ai_chat_service.chat("Test query", tenant_id="tenant-123")
            
            assert "answer" in result
            assert result["answer"] == "Response"
            assert "confidence" in result
            mock_intent.assert_called_once()
    
    def test_chat_with_tenant_id(self, ai_chat_service):
        """Test chat query with tenant ID."""
        with patch.object(ai_chat_service, '_classify_intent'), \
             patch.object(ai_chat_service, '_gather_iam_data') as mock_gather, \
             patch.object(ai_chat_service, '_build_prompt'), \
             patch.object(ai_chat_service, '_query_llm'), \
             patch.object(ai_chat_service, '_parse_response') as mock_parse:
            
            mock_gather.return_value = {}
            mock_parse.return_value = {"answer": "Response", "confidence": 0.9}
            
            result = ai_chat_service.chat("Query", tenant_id="tenant-123")
            
            # Verify tenant_id was passed to gather_iam_data
            assert mock_gather.call_args[0][1] == "tenant-123"
            assert result["answer"] == "Response"
    
    def test_chat_with_context(self, ai_chat_service):
        """Test chat query with context."""
        context = {"current_policy_id": "policy-123"}
        
        with patch.object(ai_chat_service, '_classify_intent'), \
             patch.object(ai_chat_service, '_gather_iam_data'), \
             patch.object(ai_chat_service, '_build_prompt') as mock_prompt, \
             patch.object(ai_chat_service, '_query_llm'), \
             patch.object(ai_chat_service, '_parse_response') as mock_parse:
            
            mock_prompt.return_value = "Prompt"
            mock_parse.return_value = {"answer": "Response", "confidence": 0.9}
            
            result = ai_chat_service.chat("Query", tenant_id="tenant-123", context=context)
            
            # Verify context was passed to build_prompt
            assert mock_prompt.call_args[0][3] == context
            assert result["answer"] == "Response"
    
    def test_chat_error_handling(self, ai_chat_service):
        """Test error handling in chat."""
        with patch.object(ai_chat_service, '_classify_intent', side_effect=Exception("Error")):
            result = ai_chat_service.chat("Query")
            
            assert "error" in result
            assert "answer" in result
            assert "I encountered an error" in result["answer"] or "error" in result["answer"].lower()

