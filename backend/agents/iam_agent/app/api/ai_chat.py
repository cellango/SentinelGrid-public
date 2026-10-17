"""AI Chat API endpoints for IAM Agent."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from app.models.ai_chat import (
    ChatRequest,
    ChatResponse,
    ConversationCreateRequest,
    ConversationResponse,
    ConversationWithMessages,
)
from app.api.request_context import RequestContext, get_current_request_context

router = APIRouter(prefix="/internal/iam/chat", tags=["ai-chat"])
_conversations: Dict[str, ConversationWithMessages] = {}


def get_chat_service():
    return None


def _resolve_tenant_id(
    request_context: RequestContext, requested_tenant_id: str | None = None
) -> str:
    authenticated_tenant_id = str(request_context.tenant_id)
    if requested_tenant_id and requested_tenant_id != authenticated_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied: Tenant mismatch")
    return authenticated_tenant_id


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    request_context: RequestContext = Depends(get_current_request_context),
) -> ChatResponse:
    _resolve_tenant_id(request_context, request.tenant_id)
    raise HTTPException(
        status_code=501,
        detail="Legacy IAM chat and automatic onboarding are unavailable; use the draft editor",
    )


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    request: ConversationCreateRequest,
    request_context: RequestContext = Depends(get_current_request_context),
) -> ConversationResponse:
    """Create a new conversation."""
    import uuid
    from datetime import datetime, timezone

    conversation_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    tenant_id = _resolve_tenant_id(request_context, request.tenant_id)
    conversation = ConversationWithMessages(
        id=conversation_id,
        title=request.title or "New Conversation",
        tenant_id=tenant_id,
        created_at=now,
        updated_at=now,
        message_count=0,
        messages=[],
    )
    _conversations[conversation_id] = conversation
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        tenant_id=conversation.tenant_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=conversation.message_count,
    )


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    tenant_id: str = None,
    request_context: RequestContext = Depends(get_current_request_context),
) -> List[ConversationResponse]:
    """List all conversations, optionally filtered by tenant."""
    resolved_tenant_id = _resolve_tenant_id(request_context, tenant_id)
    conversations = list(_conversations.values())
    conversations = [c for c in conversations if c.tenant_id == resolved_tenant_id]
    return [
        ConversationResponse(
            id=c.id,
            title=c.title,
            tenant_id=c.tenant_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
            message_count=c.message_count,
        )
        for c in sorted(conversations, key=lambda x: x.updated_at, reverse=True)
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: str,
    request_context: RequestContext = Depends(get_current_request_context),
) -> ConversationWithMessages:
    """Get a specific conversation with its messages."""
    if conversation_id not in _conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conversation = _conversations[conversation_id]
    if conversation.tenant_id != str(request_context.tenant_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    request_context: RequestContext = Depends(get_current_request_context),
):
    """Delete a conversation."""
    if conversation_id not in _conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conversation = _conversations[conversation_id]
    if conversation.tenant_id != str(request_context.tenant_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    del _conversations[conversation_id]


@router.get("/suggestions")
async def get_suggestions(
    query: str = None,
    tenant_id: str = None,
    request_context: RequestContext = Depends(get_current_request_context),
) -> Dict[str, Any]:
    """Get suggested queries or follow-up questions."""
    _resolve_tenant_id(request_context, tenant_id)
    suggestions = [
        "Who has access to production databases?",
        "Show me all users with the SOC_MANAGER role",
        "What policies are currently active?",
        "Create a policy for SOC analysts during business hours",
        "Who can access sensitive data?",
        "Show me all roles in the system",
    ]
    if query:
        query_lower = query.lower()
        suggestions = [s for s in suggestions if query_lower in s.lower()][:5]
    return {"suggestions": suggestions[:5]}
