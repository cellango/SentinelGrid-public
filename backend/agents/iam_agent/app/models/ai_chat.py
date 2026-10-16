"""AI Chat models for IAM Agent."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ChatMessage(BaseModel):
    """A chat message in the conversation."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Request for AI chat query."""
    query: str = Field(..., description="User's natural language query")
    tenant_id: Optional[str] = Field(None, description="Optional tenant ID for multi-tenancy")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    format: Optional[str] = Field("natural", description="Response format: 'natural' or 'json'")


class ChatResponse(BaseModel):
    """Response from AI chat."""
    answer: str = Field(..., description="AI assistant's answer")
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted entities")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    sources: List[str] = Field(default_factory=list, description="Data sources used")
    timestamp: Optional[datetime] = None
    error: Optional[str] = None


class ConversationCreateRequest(BaseModel):
    """Request to create a new conversation."""
    title: Optional[str] = Field(None, description="Optional conversation title")
    tenant_id: Optional[str] = Field(None, description="Tenant ID for multi-tenancy")


class ConversationResponse(BaseModel):
    """Conversation response."""
    id: str
    title: Optional[str] = None
    tenant_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ConversationWithMessages(ConversationResponse):
    """Conversation with its messages."""
    messages: List[ChatMessage] = Field(default_factory=list)

