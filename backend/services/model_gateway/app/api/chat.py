"""Vuln/FixGroup chat endpoint backed by fix_group embeddings."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import logging

from app.core.database import get_current_tenant, get_tenant_session
from app.api.embeddings import EmbeddingSearchRequest, search_fix_group_embeddings
from app.api.embeddings import get_embedding_service, EmbeddingsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class VulnChatRequest(BaseModel):
    tenant_id: str
    query: str
    limit: int = Field(5, ge=1, le=10)
    conversation_id: Optional[str] = None


class VulnChatResponse(BaseModel):
    reply: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    conversation_id: Optional[str] = None


def _enforce_same_tenant(requested_tenant_id: str, current_tenant_id: UUID) -> str:
    if str(requested_tenant_id) != str(current_tenant_id):
        raise HTTPException(status_code=403, detail="Cross-tenant access denied")
    return str(current_tenant_id)


def _format_sources(results) -> List[Dict[str, Any]]:
    formatted = []
    for r in results:
        formatted.append(
            {
                "fix_group_id": r.fix_group_id,
                "scanner_id": r.scanner_id,
                "target_ref": r.target_ref,
                "ticket_id": getattr(r, "ticket_id", None),
                "similarity": r.similarity,
                "summary": r.summary,
                "metadata": r.metadata,
                "timestamp": r.created_at,
            }
        )
    return formatted


@router.post("/vuln", response_model=VulnChatResponse)
def vuln_chat(
    payload: VulnChatRequest,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
    embedder: Optional[EmbeddingsService] = Depends(get_embedding_service),
):
    """
    Tenant-scoped vuln/FixGroup chat:
    - Runs fix_group embedding search.
    - Returns a templated reply with citations.
    """
    if embedder is None:
        raise HTTPException(status_code=503, detail="Embedding model not available")
    tenant_id = _enforce_same_tenant(payload.tenant_id, current_tenant_id)
    try:
        search_resp = search_fix_group_embeddings(
            EmbeddingSearchRequest(
                tenant_id=tenant_id,
                query=payload.query,
                limit=payload.limit,
            ),
            current_tenant_id=current_tenant_id,
            db=db,
        )
        results = getattr(search_resp, "results", []) or []
        logger.info(
            "vuln_chat search completed",
            extra={
                "tenant_id": tenant_id,
                "query": payload.query[:200],
                "count": len(results),
            },
        )
        if not results:
            return VulnChatResponse(
                reply="I could not find matching remediation items. Try a more specific target, scanner, or CVE.",
                sources=[],
                conversation_id=payload.conversation_id,
            )
        lines = ["Here are the closest remediation items I found:"]
        for idx, r in enumerate(results, start=1):
            sev = (r.metadata or {}).get("severity") if hasattr(r, "metadata") else None
            src = (r.metadata or {}).get("source") if hasattr(r, "metadata") else None
            ticket_txt = f", ticket {r.ticket_id}" if getattr(r, "ticket_id", None) else ""
            lines.append(
                f"{idx}. {src or 'fix_group'} {r.fix_group_id}{ticket_txt} for {r.target_ref or 'target'} "
                f"(scanner {r.scanner_id or 'unknown'}, severity {sev or 'n/a'}): {r.summary}"
            )
        lines.append("Open the scan detail page to view FixGroups, guidance, and create tickets.")
        return VulnChatResponse(
            reply="\n".join(lines),
            sources=_format_sources(results),
            conversation_id=payload.conversation_id,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "vuln_chat failed",
            extra={"tenant_id": tenant_id, "error": str(exc)},
        )
        raise HTTPException(status_code=500, detail=f"Chat failed: {exc}")
