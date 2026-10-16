import pytest
from fastapi.testclient import TestClient

def test_chat_usage_query(client: TestClient, internal_headers: dict[str, str]):
    """Test AI assistant chat with usage query"""
    response = client.post(
        "/api/v1/ai-assistant/chat",
        headers=internal_headers,
        json={
            "message": "Which apps are using the most tokens?",
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "tokens" in data["message"].lower() or "usage" in data["message"].lower()

def test_chat_injection_query(client: TestClient, internal_headers: dict[str, str]):
    """Test AI assistant chat with injection query"""
    response = client.post(
        "/api/v1/ai-assistant/chat",
        headers=internal_headers,
        json={
            "message": "Show me recent prompt injection attempts",
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "injection" in data["message"].lower()

def test_chat_policy_recommendation(client: TestClient, internal_headers: dict[str, str]):
    """Test AI assistant policy recommendations"""
    response = client.post(
        "/api/v1/ai-assistant/chat",
        headers=internal_headers,
        json={
            "message": "What policies should I enable for production?",
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "policy" in data["message"].lower() or "recommend" in data["message"].lower()

def test_chat_with_history(client: TestClient, internal_headers: dict[str, str]):
    """Test AI assistant with conversation history"""
    response = client.post(
        "/api/v1/ai-assistant/chat",
        headers=internal_headers,
        json={
            "message": "Tell me more",
            "conversation_history": [
                {"role": "user", "content": "What is AI security?"},
                {"role": "assistant", "content": "AI security protects..."},
            ]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
