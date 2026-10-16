"""Authorization evaluation API endpoints."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.request_context import (
    RequestContext,
    ensure_request_tenant_matches,
    get_current_request_context,
    get_tenant_session,
)
from app.services.evaluation_engine import EvaluationEngine, EvaluationContext
from app.services.redis_cache import cache

router = APIRouter(prefix="/api/v1/authorize", tags=["authorization"])


class AuthorizationRequest(BaseModel):
    """Schema for authorization evaluation request."""
    user_id: UUID
    tenant_id: UUID
    resource_type: str = Field(..., max_length=100)
    resource_id: str = Field(..., max_length=255)
    action: str = Field(..., max_length=50)
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context (IP, time, etc.)")


class AuthorizationResponse(BaseModel):
    """Schema for authorization evaluation response."""
    decision: str = Field(..., description="'allow' or 'deny'")
    reason: str
    matched_entitlements: List[Dict[str, Any]] = []
    evaluated_at: str


class BatchAuthorizationRequest(BaseModel):
    """Schema for batch authorization evaluation."""
    requests: List[AuthorizationRequest]


class BatchAuthorizationResponse(BaseModel):
    """Schema for batch authorization response."""
    results: List[AuthorizationResponse]


class UserEntitlementsRequest(BaseModel):
    """Schema for getting user entitlements."""
    user_id: UUID
    tenant_id: UUID
    resource_type: Optional[str] = None
    action: Optional[str] = None


@router.post("", response_model=AuthorizationResponse)
async def authorize(
    request: AuthorizationRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """
    Evaluate an access request.
    
    Returns allow/deny decision based on user entitlements and context.
    """
    ensure_request_tenant_matches(request_context.tenant_id, request.tenant_id)
    engine = EvaluationEngine(db)
    
    # Build evaluation context
    context = EvaluationContext(
        user_id=request.user_id,
        tenant_id=request.tenant_id,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        action=request.action,
        additional_context=request.context or {}
    )
    
    # Evaluate
    result = await engine.evaluate(context, use_cache=True)
    
    return AuthorizationResponse(
        decision=result.decision,
        reason=result.reason,
        matched_entitlements=result.matched_entitlements,
        evaluated_at=result.evaluated_at.isoformat()
    )


@router.post("/batch", response_model=BatchAuthorizationResponse)
async def authorize_batch(
    request: BatchAuthorizationRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """Evaluate multiple access requests in batch."""
    for access_request in request.requests:
        ensure_request_tenant_matches(request_context.tenant_id, access_request.tenant_id)

    engine = EvaluationEngine(db)
    
    # Build contexts
    contexts = [
        EvaluationContext(
            user_id=req.user_id,
            tenant_id=req.tenant_id,
            resource_type=req.resource_type,
            resource_id=req.resource_id,
            action=req.action,
            additional_context=req.context or {}
        )
        for req in request.requests
    ]
    
    # Evaluate batch
    results = await engine.evaluate_batch(contexts, use_cache=True)
    
    return BatchAuthorizationResponse(
        results=[
            AuthorizationResponse(
                decision=r.decision,
                reason=r.reason,
                matched_entitlements=r.matched_entitlements,
                evaluated_at=r.evaluated_at.isoformat()
            )
            for r in results
        ]
    )


@router.post("/user/entitlements")
async def get_user_entitlements(
    request: UserEntitlementsRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    """
    Get all entitlements for a user.
    
    Useful for UI display of user permissions.
    """
    ensure_request_tenant_matches(request_context.tenant_id, request.tenant_id)
    engine = EvaluationEngine(db)
    
    entitlements = engine.get_user_entitlements(
        user_id=request.user_id,
        tenant_id=request.tenant_id,
        resource_type=request.resource_type,
        action=request.action
    )
    
    return {
        "user_id": str(request.user_id),
        "tenant_id": str(request.tenant_id),
        "entitlements": [
            {
                "id": str(e.id),
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "action": e.action,
                "status": e.status,
                "granted_at": e.granted_at.isoformat() if e.granted_at else None,
                "expires_at": e.expires_at.isoformat() if e.expires_at else None,
                "metadata": e.metadata_json or {}
            }
            for e in entitlements
        ],
        "count": len(entitlements)
    }


@router.delete("/cache")
async def clear_evaluation_cache(
    user_id: Optional[UUID] = None,
    tenant_id: Optional[UUID] = None
    ,
    request_context: RequestContext = Depends(get_current_request_context),
):
    """
    Clear evaluation result cache.
    
    Useful for testing or when entitlements are updated.
    """
    ensure_request_tenant_matches(request_context.tenant_id, tenant_id)
    effective_tenant_id = tenant_id or request_context.tenant_id

    if user_id:
        pattern = f"evaluation:user:{user_id}:tenant:{effective_tenant_id}:*"
    else:
        pattern = f"evaluation:*:tenant:{effective_tenant_id}:*"
    
    deleted_count = cache.delete_pattern(pattern)
    
    return {
        "deleted_keys": deleted_count,
        "pattern": pattern
    }
