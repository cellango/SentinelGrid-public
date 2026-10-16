from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import ai_chat
from app.api.request_context import RequestContext, get_current_request_context
from app.models.ai_chat import ChatMessage, ConversationWithMessages


class ChatServiceSpy:
    def __init__(self):
        self.calls = []

    async def chat(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "answer": "ok",
            "entities": [],
            "confidence": 0.9,
            "sources": ["iam"],
            "timestamp": datetime.now(timezone.utc),
        }


@pytest.fixture(autouse=True)
def clear_conversations():
    ai_chat._conversations.clear()
    yield
    ai_chat._conversations.clear()


@pytest.fixture
def request_context():
    return RequestContext(
        tenant_id=uuid4(),
        user_id=str(uuid4()),
    )


@pytest.fixture
def ai_chat_test_app(request_context):
    app = FastAPI()
    app.include_router(ai_chat.router)
    app.dependency_overrides[get_current_request_context] = lambda: request_context
    return app


@pytest.fixture
def ai_chat_client(ai_chat_test_app):
    return TestClient(ai_chat_test_app)


def _override_dependency(app, dependency, value):
    app.dependency_overrides[dependency] = lambda: value


def test_chat_rejects_foreign_body_tenant(ai_chat_test_app, ai_chat_client):
    service = ChatServiceSpy()
    _override_dependency(ai_chat_test_app, ai_chat.get_chat_service, service)

    response = ai_chat_client.post(
        "/internal/iam/chat",
        headers={"authorization": "Bearer test-token"},
        json={"query": "Who has access?", "tenant_id": str(uuid4())},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert service.calls == []


def test_chat_defaults_to_authenticated_tenant(ai_chat_test_app, ai_chat_client, request_context):
    service = ChatServiceSpy()
    _override_dependency(ai_chat_test_app, ai_chat.get_chat_service, service)

    response = ai_chat_client.post(
        "/internal/iam/chat",
        headers={"authorization": "Bearer test-token"},
        json={"query": "Who has access?"},
    )

    assert response.status_code == 200
    assert service.calls[0]["tenant_id"] == str(request_context.tenant_id)
    assert service.calls[0]["user_id"] == request_context.user_id


def test_create_and_list_conversations_use_authenticated_tenant(
    ai_chat_client,
    request_context,
):
    create_response = ai_chat_client.post(
        "/internal/iam/chat/conversations",
        headers={"authorization": "Bearer test-token"},
        json={"title": "My conversation"},
    )

    assert create_response.status_code == 201
    assert create_response.json()["tenant_id"] == str(request_context.tenant_id)

    list_response = ai_chat_client.get(
        "/internal/iam/chat/conversations",
        headers={"authorization": "Bearer test-token"},
    )

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["tenant_id"] == str(request_context.tenant_id)


def test_create_conversation_rejects_foreign_body_tenant(ai_chat_client):
    response = ai_chat_client.post(
        "/internal/iam/chat/conversations",
        headers={"authorization": "Bearer test-token"},
        json={"title": "Foreign", "tenant_id": str(uuid4())},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}


def test_get_conversation_hides_foreign_tenant_record(ai_chat_client, request_context):
    conversation_id = str(uuid4())
    ai_chat._conversations[conversation_id] = ConversationWithMessages(
        id=conversation_id,
        title="Foreign",
        tenant_id=str(uuid4()),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        message_count=1,
        messages=[ChatMessage(role="user", content="hello")],
    )

    response = ai_chat_client.get(
        f"/internal/iam/chat/conversations/{conversation_id}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Conversation not found"}


def test_delete_conversation_hides_foreign_tenant_record(ai_chat_client):
    conversation_id = str(uuid4())
    ai_chat._conversations[conversation_id] = ConversationWithMessages(
        id=conversation_id,
        title="Foreign",
        tenant_id=str(uuid4()),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        message_count=0,
        messages=[],
    )

    response = ai_chat_client.delete(
        f"/internal/iam/chat/conversations/{conversation_id}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Conversation not found"}
    assert conversation_id in ai_chat._conversations


def test_suggestions_reject_foreign_query_tenant(ai_chat_client):
    response = ai_chat_client.get(
        f"/internal/iam/chat/suggestions?tenant_id={uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
