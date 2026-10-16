"""
Unified Chat API
Single chat interface for all modules (IAM, SOC, SIEM)
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import logging
import os
from datetime import datetime

from app.services.unified_chat_service import UnifiedChatService
from app.services.model_service import ModelService
from app.services.audit_client import AuditClient
from sg_core.security import verify_token, security as bearer_security
from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials

router = APIRouter(prefix="/internal/llm", tags=["chat"])
logger = logging.getLogger(__name__)

# Initialize services
chat_service = UnifiedChatService()
model_service = ModelService()
audit_client = AuditClient()


class ChatRequest(BaseModel):
    """Chat request model."""
    query: str = Field(..., description="User query")
    tenant_id: str = Field(..., description="Tenant ID")
    module: Optional[str] = Field(None, description="Explicit module (iam, soc, siem, compliance) - auto-detected if not provided")
    active_agent: Optional[str] = Field(None, description="Frontend-selected active agent, such as compliance_agent")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context (current incident, policy, etc.)")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str = Field(..., description="AI response text")
    module: str = Field(..., description="Detected or specified module")
    tenant_id: str = Field(..., description="Tenant ID")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="RAG sources used")
    confidence: float = Field(..., description="Confidence score (0-1)")
    generated_at: str = Field(..., description="Generation timestamp")
    model_metadata: Dict[str, Any] = Field(default_factory=dict, description="Model information")
    answer_type: str = Field(default="knowledge_base", description="Response provenance label")
    source_kind: str = Field(default="knowledge_base", description="Primary source class for the answer")
    retrieval_categories: List[str] = Field(default_factory=list, description="Retrieval categories used")
    actions: List[Dict[str, Any]] = Field(default_factory=list, description="Optional proposed actions")


@router.post("/chat", response_model=ChatResponse, summary="Unified Chat Interface")
async def chat(
    request: ChatRequest,
    credentials: HTTPAuthorizationCredentials = Security(bearer_security),
):
    """
    Unified chat interface for all SentinelGrid modules.
    
    Automatically detects module (IAM, SOC, SIEM) from query or uses explicit module.
    Uses tenant-specific LoRA adapter and RAG context for personalized responses.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=403, detail="Missing bearer token")

    token_payload = verify_token(credentials.credentials)
    token_tenant = token_payload.get("tenant_id")
    realm = token_payload.get("realm") or token_payload.get("realm_name") or (request.context.get("realm") if request.context else None)

    if not token_tenant:
        raise HTTPException(status_code=403, detail="Invalid token: missing tenant_id")
    if request.tenant_id and request.tenant_id != token_tenant:
        raise HTTPException(status_code=403, detail="Tenant mismatch between token and request")
    if not realm:
        raise HTTPException(status_code=400, detail="realm is required for AI activity")

    effective_tenant_id = token_tenant

    use_llm = os.getenv("ENABLE_LLM_CHAT", "false").lower() in ("1", "true", "yes")
    try:
        request_context = dict(request.context or {})
        if request.active_agent and "active_agent" not in request_context:
            request_context["active_agent"] = request.active_agent

        # Process chat query
        result = chat_service.process_chat_query(
            query=request.query,
            tenant_id=effective_tenant_id,
            module=request.module,
            context=request_context
        )
        sources = result.get("sources", [])
        module = result.get("module", "general")
        generated_at = datetime.utcnow().isoformat()
        
        if use_llm:
            # Generate response using model service (heavier path)
            model_result = model_service.generate_with_adapter(
                tenant_id=effective_tenant_id,
                prompt=result.get("prompt", request.query),
                max_tokens=int(os.getenv("CHAT_MAX_TOKENS", "192")),
                temperature=0.6,
            )
            reply_text = model_result.get("text", "Unable to generate response.").strip()
            model_metadata = {
                "model_name": model_result.get("model_name"),
                "adapter_used": model_result.get("adapter_used", False),
                "adapter_version": model_result.get("adapter_version"),
                "tokens": model_result.get("tokens", 0),
            }
        else:
            # Fast fallback: summarize relevant sources without invoking the LLM
            reply_text = _build_fallback_reply(request.query, module, sources, request_context, result)
            model_metadata = {
                "model_name": "fast-fallback",
                "adapter_used": False,
                "adapter_version": None,
                "tokens": 0,
            }
        
        # Combine results
        response = ChatResponse(
            response=reply_text or "No response generated.",
            module=module,
            tenant_id=effective_tenant_id,
            sources=sources,
            confidence=result.get("confidence", 0.8),
            generated_at=generated_at,
            model_metadata=model_metadata,
            answer_type=result.get("answer_type", "knowledge_base"),
            source_kind=result.get("source_kind", result.get("answer_type", "knowledge_base")),
            retrieval_categories=result.get("retrieval_categories", []),
            actions=result.get("actions", []),
        )

        # Fire-and-forget audit log for AI activity
        try:
            import asyncio
            asyncio.create_task(
                audit_client.log_ai_event({
                    "tenant_id": effective_tenant_id,
                    "realm_name": realm,
                    "action": "unified_chat",
                    "action_category": "ai",
                    "actor_user_id": request.context.get("user_id") if request.context else None,
                    "metadata": {
                        "query": request.query[:500],
                        "module": module,
                        "answer_type": response.answer_type,
                        "source_kind": response.source_kind,
                        "retrieval_categories": response.retrieval_categories,
                        "compliance_accessed_categories": (
                            (request_context.get("compliance_live_context") or {}).get("accessed_categories", [])
                            if module == "compliance"
                            else []
                        ),
                        "sources": [{"title": s.get("title"), "similarity": s.get("similarity")} for s in sources],
                        "model": model_metadata.get("model_name"),
                        "adapter_used": model_metadata.get("adapter_used"),
                        "adapter_version": model_metadata.get("adapter_version"),
                        "reply_preview": reply_text[:500],
                    }
                })
            )
        except Exception as e:
            logger.warning(f"Failed to enqueue AI audit log: {e}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error in unified chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat request: {str(e)}"
        )


def _build_fallback_reply(
    query: str,
    module: str,
    sources: List[Dict[str, Any]],
    context: Dict[str, Any] | None = None,
    result: Dict[str, Any] | None = None,
) -> str:
    """Lightweight, deterministic reply using RAG sources."""
    if module == "compliance":
        return _build_compliance_fallback_reply(query, sources, context or {}, result or {})

    if not sources:
        return (
            f"I could not find specific knowledge base matches for \"{query}\" right now. "
            "Try a more detailed question or load additional content."
        )
    lines = ["Here are the closest references:"]
    for idx, src in enumerate(sources[:3], 1):
        snippet = (src.get("content") or "")[:320].replace("\n", " ").strip()
        title = src.get("title") or "Reference"
        category = src.get("category") or "kb"
        lines.append(f"[{idx}] {title} ({category}): {snippet}")
    lines.append("Ask a follow-up for more detail.")
    return "\n".join(lines)


def _build_compliance_fallback_reply(
    query: str,
    sources: List[Dict[str, Any]],
    context: Dict[str, Any],
    result: Dict[str, Any],
) -> str:
    """Deterministic compliance reply that labels live status versus references."""
    live_context = context.get("compliance_live_context") or {}
    coverage = live_context.get("coverage") or {}
    evidence = live_context.get("evidence") or {}
    reports = live_context.get("reports") or {}
    recommendations = live_context.get("recommendations") or {}
    actions = result.get("actions") or []

    if live_context:
        lines = ["Live compliance status, not an audit attestation:"]
        if coverage.get("status") == "available":
            lines.append(
                f"- Frameworks in scope: {coverage.get('framework_count', 0)}; "
                f"high-priority gaps: {coverage.get('high_priority_gap_count', 0)}."
            )
            for framework in (coverage.get("items") or [])[:3]:
                label = framework.get("framework_name") or framework.get("framework_id") or "Framework"
                lines.append(
                    f"- {label}: {framework.get('status', 'unknown')} "
                    f"({framework.get('control_count', 0)} controls)."
                )
            for gap in (coverage.get("high_priority_gaps") or [])[:3]:
                lines.append(
                    f"- Gap {gap.get('control_id') or 'control'}: "
                    f"{gap.get('title') or gap.get('summary') or 'review required'} "
                    f"({gap.get('severity', 'high')})."
                )
        else:
            lines.append("- Live coverage was unavailable for this request.")

        if evidence.get("status") == "available":
            lines.append(f"- Evidence items sampled: {len(evidence.get('items') or [])} of {evidence.get('count', 0)}.")
        if reports.get("status") == "available":
            lines.append(f"- Reports sampled: {len(reports.get('items') or [])} of {reports.get('count', 0)}.")
        if recommendations.get("status") == "available":
            lines.append(f"- Proposed Compliance Agent recommendations: {recommendations.get('count', 0)}.")
        if actions:
            lines.append("- Proposed agent action available for human review before any write action runs.")

        lines.append("Use the linked evidence, reports, and recommendation review flow before treating this as audit-ready.")
        return "\n".join(lines)

    if sources:
        lines = ["Compliance knowledge base reference, not tenant-specific live status:"]
        for idx, src in enumerate(sources[:3], 1):
            snippet = (src.get("content") or "")[:300].replace("\n", " ").strip()
            title = src.get("title") or "Reference"
            category = src.get("category") or "kb"
            lines.append(f"[{idx}] {title} ({category}): {snippet}")
        return "\n".join(lines)

    return (
        f"I could not retrieve live compliance context or knowledge base matches for \"{query}\". "
        "No compliance determination was made."
    )


@router.post("/chat/stream", summary="Streaming Chat Interface")
async def chat_stream(request: ChatRequest):
    """
    Streaming chat interface for real-time responses.
    
    Uses Server-Sent Events (SSE) to stream tokens as they're generated.
    """
    # TODO: Implement streaming response
    # Would use async generators and SSE
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Streaming not yet implemented"
    )
