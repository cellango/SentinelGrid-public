from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_internal_service_token
from app import schemas

router = APIRouter()

@router.post("/chat", response_model=schemas.ChatResponse)
def chat_with_assistant(
    request: schemas.ChatRequest,
    _: str = Depends(require_internal_service_token),
    db: Session = Depends(get_db),
):
    """Chat with AI Security Assistant"""
    # Simplified implementation - would integrate with model_gateway
    message = request.message.lower()
    
    # Simple pattern matching for demo
    if "usage" in message or "tokens" in message:
        return schemas.ChatResponse(
            message="Based on recent data, your top apps by token usage are: CustomerSupport (1.2M tokens), DataAnalysis (800K tokens), and ChatBot (500K tokens) this week.",
            data={"top_apps": ["CustomerSupport", "DataAnalysis", "ChatBot"]}
        )
    elif "injection" in message or "attack" in message:
        return schemas.ChatResponse(
            message="I found 3 prompt injection attempts in the last 24 hours, all from the CustomerSupport app. They appear to be testing patterns, not actual attacks.",
            data={"injection_count": 3, "app": "CustomerSupport"}
        )
    elif "policy" in message or "recommend" in message:
        return schemas.ChatResponse(
            message="For production environments, I recommend: 1) Block secrets outbound (enabled by default), 2) Enable PII detection for sensitive apps, 3) Set jailbreak detection threshold to 0.7+",
            data={"recommendations": ["block_secrets", "enable_pii", "jailbreak_threshold_0.7"]}
        )
    else:
        return schemas.ChatResponse(
            message=f"I can help you with AI security questions. Try asking about token usage, prompt injections, or policy recommendations.",
            data=None
        )
