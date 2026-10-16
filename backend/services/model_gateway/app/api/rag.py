"""RAG API endpoints for knowledge base management and search."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.core.database import get_current_tenant, get_tenant_session
from app.services.rag_service import RAGService

router = APIRouter(prefix="/internal/llm/rag", tags=["RAG"])


class KnowledgeEntryRequest(BaseModel):
    """Request model for storing knowledge."""
    category: str = Field(..., description="Category (nist, mitre, owasp, etc.)")
    title: str = Field(..., description="Entry title")
    content: str = Field(..., description="Entry content")
    tenant_id: Optional[str] = Field(None, description="Tenant ID (None for shared)")
    subcategory: Optional[str] = Field(None, description="Subcategory")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    source_url: Optional[str] = Field(None, description="Source URL")
    framework_version: Optional[str] = Field(None, description="Framework version")


class BulkKnowledgeRequest(BaseModel):
    """Request model for bulk storing knowledge."""
    entries: List[KnowledgeEntryRequest]
    tenant_id: Optional[str] = Field(None, description="Default tenant ID for all entries")


class SearchRequest(BaseModel):
    """Request model for RAG search."""
    query: str = Field(..., description="Search query")
    tenant_id: Optional[str] = Field(None, description="Tenant ID")
    category: Optional[str] = Field(None, description="Category filter")
    top_k: int = Field(5, ge=1, le=50, description="Number of results")


def _resolve_effective_tenant_id(
    requested_tenant_id: Optional[str],
    current_tenant_id: UUID,
) -> str:
    effective_tenant_id = requested_tenant_id or str(current_tenant_id)
    if str(effective_tenant_id) != str(current_tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access denied",
        )
    return str(current_tenant_id)


@router.post("/knowledge", response_model=Dict[str, Any])
def store_knowledge(
    request: KnowledgeEntryRequest,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Store a knowledge base entry."""
    effective_tenant_id = _resolve_effective_tenant_id(request.tenant_id, current_tenant_id)
    service = RAGService(db_session=db)
    
    result = service.store_knowledge(
        category=request.category,
        title=request.title,
        content=request.content,
        tenant_id=effective_tenant_id,
        subcategory=request.subcategory,
        metadata=request.metadata,
        source_url=request.source_url,
        framework_version=request.framework_version
    )
    
    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to store knowledge")
        )
    
    return result


@router.post("/knowledge/bulk", response_model=Dict[str, Any])
def bulk_store_knowledge(
    request: BulkKnowledgeRequest,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Bulk store knowledge base entries."""
    effective_tenant_id = _resolve_effective_tenant_id(request.tenant_id, current_tenant_id)
    for entry in request.entries:
        if entry.tenant_id is not None:
            _resolve_effective_tenant_id(entry.tenant_id, current_tenant_id)
    service = RAGService(db_session=db)
    
    entries = [
        {
            "category": entry.category,
            "title": entry.title,
            "content": entry.content,
            "tenant_id": entry.tenant_id or effective_tenant_id,
            "subcategory": entry.subcategory,
            "metadata": entry.metadata,
            "source_url": entry.source_url,
            "framework_version": entry.framework_version
        }
        for entry in request.entries
    ]
    
    result = service.bulk_store(entries, tenant_id=effective_tenant_id)
    
    return result


@router.post("/search", response_model=List[Dict[str, Any]])
def search_knowledge(
    request: SearchRequest,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Search knowledge base using vector similarity."""
    effective_tenant_id = _resolve_effective_tenant_id(request.tenant_id, current_tenant_id)
    service = RAGService(db_session=db)
    
    results = service.search(
        query=request.query,
        tenant_id=effective_tenant_id,
        category=request.category,
        top_k=request.top_k
    )
    
    return results


@router.get("/search", response_model=List[Dict[str, Any]])
def search_knowledge_get(
    query: str,
    tenant_id: Optional[str] = None,
    category: Optional[str] = None,
    top_k: int = 5,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Search knowledge base (GET version)."""
    effective_tenant_id = _resolve_effective_tenant_id(tenant_id, current_tenant_id)
    service = RAGService(db_session=db)
    
    results = service.search(
        query=query,
        tenant_id=effective_tenant_id,
        category=category,
        top_k=min(top_k, 50)  # Cap at 50
    )
    
    return results
