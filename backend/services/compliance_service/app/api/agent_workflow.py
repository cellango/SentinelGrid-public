"""Compliance Agent supervised workflow endpoints."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from sg_core.security import get_current_payload

from app.core.config import settings
from app.core.database import get_current_tenant, get_tenant_session
from app.services.observability import record_agent_recommendation_decision

from sg_agent_runtime.compliance_workflow import (
    ComplianceAgentRecommendationRepository,
    ComplianceAgentRuntimeClient,
    ComplianceAgentWorkflowError,
    ComplianceAgentWorkflowService,
)

router = APIRouter(prefix="/api/v1/compliance/agent", tags=["compliance-agent"])


RECOMMENDATION_REVIEW_ROLES = {
    "admin",
    "tenant_admin",
    "compliance_manager",
    "compliance_officer",
    "evidence_reviewer",
    "soc_manager",
}


class RecommendationDecisionRequest(BaseModel):
    state: str = Field(..., description="accepted, rejected, or superseded")
    decision_notes: Optional[str] = None
    superseded_by: Optional[str] = None


def _normalize_role(role: str) -> str:
    return role.strip().lower().replace("-", "_").replace(" ", "_")


def _roles_from_payload(token_payload: dict[str, Any]) -> set[str]:
    roles = token_payload.get("roles") or token_payload.get("realm_roles") or []
    return {_normalize_role(str(role)) for role in roles if str(role).strip()}


def _require_role(token_payload: dict[str, Any], allowed_roles: set[str]) -> None:
    if not _roles_from_payload(token_payload).intersection(allowed_roles):
        raise HTTPException(status_code=403, detail="Required compliance agent role not found")


def _actor_id(token_payload: dict[str, Any], actor_header: str | None = None) -> str:
    return (
        actor_header
        or token_payload.get("user_id")
        or token_payload.get("sub")
        or token_payload.get("preferred_username")
        or "authenticated_user"
    )


def get_recommendation_repository() -> ComplianceAgentRecommendationRepository:
    return ComplianceAgentRecommendationRepository()


def get_compliance_agent_workflow_service() -> ComplianceAgentWorkflowService:
    return ComplianceAgentWorkflowService(
        repository=ComplianceAgentRecommendationRepository(),
        runtime_client=ComplianceAgentRuntimeClient(
            runtime_url=settings.AGENT_RUNTIME_URL,
            internal_token=settings.INTERNAL_SERVICE_TOKEN,
            timeout_seconds=settings.COMPLIANCE_AGENT_TRIGGER_TIMEOUT_SECONDS,
        ),
        enabled=settings.COMPLIANCE_AGENT_ENABLED,
    )


@router.get("/recommendations")
def list_agent_recommendations(
    state: Optional[str] = Query(None),
    trigger_type: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    framework_id: Optional[str] = Query(None),
    control_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    repository: ComplianceAgentRecommendationRepository = Depends(get_recommendation_repository),
):
    """List reviewable Compliance Agent recommendations for the current tenant."""
    return repository.list_recommendations(
        db,
        current_tenant,
        state=state,
        trigger_type=trigger_type,
        source_type=source_type,
        framework_id=framework_id,
        control_id=control_id,
        limit=limit,
        offset=offset,
    )


@router.post("/recommendations/{recommendation_id}/decision")
def decide_agent_recommendation(
    recommendation_id: str,
    request: RecommendationDecisionRequest,
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    actor_header: Optional[str] = Header(None, alias="X-User-ID"),
    repository: ComplianceAgentRecommendationRepository = Depends(get_recommendation_repository),
):
    """Accept, reject, or supersede a Compliance Agent recommendation."""
    _require_role(token_payload, RECOMMENDATION_REVIEW_ROLES)
    try:
        recommendation = repository.record_decision(
            db,
            tenant_id=current_tenant,
            recommendation_id=recommendation_id,
            state=request.state,
            decided_by=_actor_id(token_payload, actor_header),
            decision_notes=request.decision_notes,
            superseded_by=request.superseded_by,
        )
    except ComplianceAgentWorkflowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not recommendation:
        raise HTTPException(status_code=404, detail="Compliance Agent recommendation not found")
    record_agent_recommendation_decision(
        state=request.state,
        trigger_type=recommendation.get("trigger_type") if isinstance(recommendation, dict) else None,
    )
    return recommendation
