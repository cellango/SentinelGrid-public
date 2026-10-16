"""NIST Compliance API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.api.request_context import RequestContext, get_current_request_context
from app.models.compliance import (
    ControlRequest,
    ControlResponse,
    ComplianceStatusRequest,
    ComplianceStatusResponse,
    ComplianceGapResponse,
    ComplianceReportRequest,
    ComplianceReportResponse,
    EvidenceCollectionRequest,
    EvidenceCollectionResponse,
    EvidenceRecordRequest,
    EvidenceRecordResponse,
    ControlCategory,
    ReportType,
    EvidenceType
)
from app.services.nist_controls import NISTControlsService
from app.services.nist_controls import ControlCategory as NISTCategory
from app.services.compliance_tracking import ComplianceTrackingService
from app.services.evidence_collection import EvidenceCollectionService
from app.services.compliance_evidence_repository import ComplianceEvidenceRepositoryClient
from app.services.keycloak_client import KeycloakClient
from app.api.auth import get_keycloak_client

router = APIRouter(prefix="/internal/iam/compliance", tags=["compliance"])


def get_nist_service() -> NISTControlsService:
    """Get NIST controls service instance."""
    return NISTControlsService()


def get_compliance_service() -> ComplianceTrackingService:
    """Get compliance tracking service instance."""
    return ComplianceTrackingService()


def get_evidence_service(
    keycloak_client: KeycloakClient = Depends(get_keycloak_client)
) -> EvidenceCollectionService:
    """Get evidence collection service instance."""
    return EvidenceCollectionService(keycloak_client)


def _resolve_tenant_id(
    request_context: RequestContext,
    requested_tenant_id: Optional[str] = None,
) -> str:
    authenticated_tenant_id = str(request_context.tenant_id)
    if requested_tenant_id is not None and requested_tenant_id != authenticated_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied: Tenant mismatch")
    return authenticated_tenant_id


@router.get("/controls", response_model=ControlResponse)
async def get_controls(
    category: Optional[ControlCategory] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
    nist_service: NISTControlsService = Depends(get_nist_service)
) -> ControlResponse:
    """Get NIST 800-53 IAM controls."""
    try:
        if category:
            nist_category = NISTCategory(category.value)
            controls = nist_service.get_iam_controls(nist_category)
        else:
            controls = nist_service.get_iam_controls()
        
        return ControlResponse(
            controls=controls,
            total_count=len(controls)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching controls: {str(e)}")


@router.get("/controls/{control_id}")
async def get_control(
    control_id: str,
    request_context: RequestContext = Depends(get_current_request_context),
    nist_service: NISTControlsService = Depends(get_nist_service)
) -> Dict[str, Any]:
    """Get a specific NIST control."""
    try:
        control = nist_service.get_control(control_id)
        if not control:
            raise HTTPException(status_code=404, detail=f"Control {control_id} not found")
        return control
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching control: {str(e)}")


@router.get("/status", response_model=ComplianceStatusResponse)
async def get_compliance_status(
    tenant_id: Optional[str] = Query(None),
    control_ids: Optional[List[str]] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
    compliance_service: ComplianceTrackingService = Depends(get_compliance_service)
) -> ComplianceStatusResponse:
    """Get compliance status for a tenant."""
    try:
        resolved_tenant_id = _resolve_tenant_id(request_context, tenant_id)
        status = compliance_service.track_compliance_status(resolved_tenant_id, control_ids)
        return ComplianceStatusResponse(**status)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error tracking compliance status: {str(e)}")


@router.get("/gaps", response_model=ComplianceGapResponse)
async def get_compliance_gaps(
    tenant_id: Optional[str] = Query(None),
    category: Optional[ControlCategory] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
    compliance_service: ComplianceTrackingService = Depends(get_compliance_service)
) -> ComplianceGapResponse:
    """Get compliance gaps for a tenant."""
    try:
        resolved_tenant_id = _resolve_tenant_id(request_context, tenant_id)
        nist_category = NISTCategory(category.value) if category else None
        gaps = compliance_service.get_compliance_gaps(resolved_tenant_id, nist_category)
        
        return ComplianceGapResponse(
            tenant_id=resolved_tenant_id,
            gaps=gaps,
            total_gaps=len(gaps),
            high_priority_gaps=len([g for g in gaps if g.get("priority") == "high"])
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting compliance gaps: {str(e)}")


@router.post("/reports", response_model=ComplianceReportResponse)
async def generate_compliance_report(
    request: ComplianceReportRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    compliance_service: ComplianceTrackingService = Depends(get_compliance_service)
) -> ComplianceReportResponse:
    """Generate a compliance report."""
    try:
        resolved_tenant_id = _resolve_tenant_id(request_context, request.tenant_id)
        nist_category = NISTCategory(request.category.value) if request.category else None
        report = compliance_service.generate_compliance_report(
            resolved_tenant_id,
            request.report_type.value,
            nist_category,
            request.start_date,
            request.end_date
        )
        
        return ComplianceReportResponse(
            tenant_id=resolved_tenant_id,
            report_type=request.report_type.value,
            report_period=report.get("report_period", {}),
            data=report,
            generated_at=datetime.fromisoformat(report.get("generated_at", datetime.utcnow().isoformat()))
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")


@router.post("/evidence/collect", response_model=EvidenceCollectionResponse)
async def collect_evidence(
    request: EvidenceCollectionRequest,
    http_request: Request,
    request_context: RequestContext = Depends(get_current_request_context),
    evidence_service: EvidenceCollectionService = Depends(get_evidence_service)
) -> EvidenceCollectionResponse:
    """Collect evidence for a control."""
    try:
        resolved_tenant_id = _resolve_tenant_id(request_context, request.tenant_id)
        # Convert string enum to EvidenceType enum
        evidence_types = [EvidenceType(et.value) if isinstance(et, str) else et for et in request.evidence_types]
        
        result = evidence_service.collect_control_evidence(
            request.control_id,
            evidence_types,
            resolved_tenant_id,
            repository_client=ComplianceEvidenceRepositoryClient(
                tenant_id=resolved_tenant_id,
                authorization_header=http_request.headers.get("authorization")
                or http_request.headers.get("Authorization"),
                actor_id=request_context.user_id,
            ),
            actor_id=request_context.user_id,
        )
        
        return EvidenceCollectionResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error collecting evidence: {str(e)}")


@router.post("/evidence/record", response_model=EvidenceRecordResponse)
async def record_evidence(
    request: EvidenceRecordRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    compliance_service: ComplianceTrackingService = Depends(get_compliance_service)
) -> EvidenceRecordResponse:
    """Record evidence for a control assessment."""
    try:
        resolved_tenant_id = _resolve_tenant_id(request_context, request.tenant_id)
        result = compliance_service.record_evidence(
            request.control_id,
            request.evidence,
            resolved_tenant_id
        )
        
        return EvidenceRecordResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording evidence: {str(e)}")


@router.get("/evidence/{control_id}")
async def get_control_evidence(
    control_id: str,
    tenant_id: Optional[str] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
    evidence_service: EvidenceCollectionService = Depends(get_evidence_service)
) -> Dict[str, Any]:
    """Get collected evidence for a specific control."""
    try:
        resolved_tenant_id = _resolve_tenant_id(request_context, tenant_id)
        # Collect standard evidence types for the control
        evidence_types = [
            EvidenceType.CONFIGURATION,
            EvidenceType.AUDIT_LOG,
            EvidenceType.POLICY_DOCUMENT
        ]
        
        result = evidence_service.collect_control_evidence(
            control_id,
            evidence_types,
            resolved_tenant_id
        )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting evidence: {str(e)}")
