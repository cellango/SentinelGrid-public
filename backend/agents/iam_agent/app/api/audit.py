"""Audit and Accountability API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.api.request_context import RequestContext, get_current_request_context
from app.models.audit import (
    AuditEventRequest,
    AuditEventResponse,
    AuditLogQuery,
    AuditLogResponse,
    AuditReviewRequest,
    AuditReviewResponse,
    AuditAnalysisResponse,
    AuditEventType,
    AuditSeverity
)
from app.services.audit_service import AuditService
# Note: AuditEventType and AuditSeverity may not exist in audit_service.py
# If needed, define them or remove the import
from app.services.keycloak_client import KeycloakClient
from app.api.auth import get_keycloak_client

router = APIRouter(prefix="/internal/iam/audit", tags=["audit"])


def _resolve_tenant_id(
    request_context: RequestContext,
    requested_tenant_id: Optional[str] = None,
) -> Optional[str]:
    authenticated_tenant_id = str(request_context.tenant_id)
    if requested_tenant_id is not None and requested_tenant_id != authenticated_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied: Tenant mismatch")
    return authenticated_tenant_id


def get_audit_service(
    keycloak_client: KeycloakClient = Depends(get_keycloak_client)
) -> AuditService:
    """Get audit service instance."""
    # AuditService doesn't take keycloak_client in its constructor
    return AuditService()


@router.post("/events", response_model=AuditEventResponse)
async def log_audit_event(
    request: AuditEventRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    audit_service: AuditService = Depends(get_audit_service)
) -> AuditEventResponse:
    """Log an audit event."""
    try:
        # Use the enum values directly from the request model
        event = audit_service.log_audit_event(
            event_type=request.event_type.value,
            actor_id=request.actor_id,
            action=request.action,
            target_resource=request.target_resource,
            target_user=request.target_user,
            outcome=request.outcome,
            severity=request.severity.value,
            details=request.details,
            tenant_id=_resolve_tenant_id(request_context, request.tenant_id)
        )
        
        return AuditEventResponse(**event)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error logging audit event: {str(e)}")


@router.get("/logs", response_model=AuditLogResponse)
async def get_audit_logs(
    tenant_id: Optional[str] = Query(None),
    event_types: Optional[List[str]] = Query(None),
    actor_id: Optional[str] = Query(None),
    target_user: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    request_context: RequestContext = Depends(get_current_request_context),
    audit_service: AuditService = Depends(get_audit_service)
) -> AuditLogResponse:
    """Get audit logs with filtering."""
    try:
        # Convert string event types to enum values
        event_type_enums = None
        if event_types:
            # Use the string values directly or convert to enum if needed
            event_type_enums = event_types
        
        severity_enum = None
        if severity:
            # Use the string value directly
            severity_enum = severity
        
        result = audit_service.get_audit_logs(
            tenant_id=_resolve_tenant_id(request_context, tenant_id),
            event_types=event_type_enums,
            actor_id=actor_id,
            target_user=target_user,
            start_date=start_date,
            end_date=end_date,
            severity=severity_enum,
            limit=limit,
            offset=offset
        )
        
        return AuditLogResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving audit logs: {str(e)}")


@router.post("/reviews", response_model=AuditReviewResponse)
async def create_audit_review(
    request: AuditReviewRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    audit_service: AuditService = Depends(get_audit_service)
) -> AuditReviewResponse:
    """Create an audit review."""
    try:
        review = audit_service.create_audit_review(
            review_name=request.review_name,
            scope=request.scope,
            reviewer_id=request.reviewer_id,
            tenant_id=_resolve_tenant_id(request_context, request.tenant_id)
        )
        
        return AuditReviewResponse(
            review_id=review["review_id"],
            review_name=review["review_name"],
            status=review["status"],
            created_at=datetime.fromisoformat(review["created_at"]),
            due_date=datetime.fromisoformat(review["due_date"]) if review.get("due_date") else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating audit review: {str(e)}")


@router.post("/reviews/{review_id}/complete")
async def complete_audit_review(
    review_id: str,
    findings: List[Dict[str, Any]],
    conclusion: str,
    reviewer_id: str = Query(...),
    request_context: RequestContext = Depends(get_current_request_context),
    audit_service: AuditService = Depends(get_audit_service)
) -> Dict[str, Any]:
    """Complete an audit review."""
    try:
        result = audit_service.perform_audit_review(
            review_id=review_id,
            findings=findings,
            conclusion=conclusion,
            reviewer_id=request_context.user_id or reviewer_id
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error completing audit review: {str(e)}")


@router.get("/analysis", response_model=AuditAnalysisResponse)
async def analyze_audit_patterns(
    tenant_id: Optional[str] = Query(None),
    time_window_days: int = Query(30, ge=1, le=365),
    request_context: RequestContext = Depends(get_current_request_context),
    audit_service: AuditService = Depends(get_audit_service)
) -> AuditAnalysisResponse:
    """Analyze audit logs for patterns and anomalies."""
    try:
        result = audit_service.analyze_audit_patterns(
            tenant_id=_resolve_tenant_id(request_context, tenant_id),
            time_window_days=time_window_days
        )
        
        return AuditAnalysisResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing audit patterns: {str(e)}")


@router.get("/statistics")
async def get_audit_statistics(
    tenant_id: Optional[str] = Query(None),
    time_window_days: int = Query(30, ge=1, le=365),
    request_context: RequestContext = Depends(get_current_request_context),
    audit_service: AuditService = Depends(get_audit_service)
) -> Dict[str, Any]:
    """Get audit statistics and metrics."""
    try:
        result = audit_service.get_audit_statistics(
            tenant_id=_resolve_tenant_id(request_context, tenant_id),
            time_window_days=time_window_days
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting audit statistics: {str(e)}")


@router.post("/export")
async def export_audit_logs(
    export_format: str = Query("json", regex="^(json|csv)$"),
    tenant_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
    audit_service: AuditService = Depends(get_audit_service)
) -> Dict[str, Any]:
    """Export audit logs for compliance."""
    try:
        result = audit_service.export_audit_logs(
            export_format=export_format,
            tenant_id=_resolve_tenant_id(request_context, tenant_id),
            start_date=start_date,
            end_date=end_date
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting audit logs: {str(e)}")
