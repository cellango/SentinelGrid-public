"""AI Chat API endpoints for IAM Agent."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any

from app.models.ai_chat import (
    ChatRequest,
    ChatResponse,
    ConversationCreateRequest,
    ConversationResponse,
    ConversationWithMessages,
    ChatMessage
)
from app.services.keycloak_client import KeycloakClient
from app.services.ai_chat_service import IAMChatService
from app.api.auth import get_keycloak_client
from app.api.request_context import RequestContext, get_current_request_context

router = APIRouter(prefix="/internal/iam/chat", tags=["ai-chat"])

# In-memory conversation storage (use database in production)
_conversations: Dict[str, ConversationWithMessages] = {}


def get_chat_service(keycloak_client: KeycloakClient = Depends(get_keycloak_client)) -> IAMChatService:
    """Get or create AI chat service instance."""
    return IAMChatService(keycloak_client)


def _resolve_tenant_id(
    request_context: RequestContext,
    requested_tenant_id: str | None = None,
) -> str:
    authenticated_tenant_id = str(request_context.tenant_id)
    if requested_tenant_id and requested_tenant_id != authenticated_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied: Tenant mismatch")
    return authenticated_tenant_id


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    chat_service: IAMChatService = Depends(get_chat_service)
) -> ChatResponse:
    """
    Process a natural language IAM query.
    
    Examples:
    - "Who has access to production databases?"
    - "Create a policy that allows SOC analysts to read alerts during business hours"
    - "Show me all users with the SOC_MANAGER role"
    """
    try:
        tenant_id = _resolve_tenant_id(request_context, request.tenant_id)
        # Get conversation history if conversation_id provided
        conversation_history = None
        user_id = request_context.user_id
        
        if request.conversation_id and request.conversation_id in _conversations:
            conversation = _conversations[request.conversation_id]
            if conversation.tenant_id != tenant_id:
                raise HTTPException(status_code=404, detail="Conversation not found")
            conversation_history = [
                {"role": msg.role, "content": msg.content}
                for msg in conversation.messages
            ]
        
        # Process chat query
        result = await chat_service.chat(
            query=request.query,
            tenant_id=tenant_id,
            context=request.context,
            user_id=user_id,
            conversation_history=conversation_history
        )
        
        # Store conversation if conversation_id provided
        if request.conversation_id:
            if request.conversation_id in _conversations:
                conversation = _conversations[request.conversation_id]
                conversation.messages.append(
                    ChatMessage(role="user", content=request.query)
                )
                conversation.messages.append(
                    ChatMessage(role="assistant", content=result.get("answer", ""))
                )
                conversation.message_count = len(conversation.messages)
                
                # Store onboarding state if present
                if result.get("onboarding_state"):
                    if not hasattr(conversation, "metadata"):
                        conversation.metadata = {}
                    conversation.metadata["onboarding_state"] = result["onboarding_state"]
        
        return ChatResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat query: {str(e)}")


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
        messages=[]
    )
    
    _conversations[conversation_id] = conversation
    
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        tenant_id=conversation.tenant_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=conversation.message_count
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
            message_count=c.message_count
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
        # Filter suggestions based on query
        query_lower = query.lower()
        suggestions = [s for s in suggestions if query_lower in s.lower()][:5]
    
    return {
        "suggestions": suggestions[:5]
    }
