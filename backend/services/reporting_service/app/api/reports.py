"""Report API endpoints."""

import os
import sys
import logging
from typing import Any, List, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

# Add libs directory to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)
else:
    sys.path.insert(0, "/app/libs")

from app.core.database import get_tenant_session
from sg_core.security import get_current_payload, get_current_tenant
from app.models.report import Report, ReportTemplate, ReportStatus, ReportFormat
from app.models.template import (
    ReportGenerateRequest,
    ReportResponse,
    ReportTemplateCreate,
    ReportTemplateResponse
)
from app.services.report_generator import ReportGeneratorService
from app.services.ai_governance_reporting import AiGovernanceReportingService
from app.services.questionnaire_assist import QuestionnaireAssistService
from app.services.report_access import (
    actor_id_from_payload,
    audit_report_event,
    enforce_report_template_roles,
    enforce_template_roles,
)
from app.core.config import settings
from sg_agent_runtime.compliance_workflow import (
    ComplianceAgentRecommendationRepository,
    ComplianceAgentRuntimeClient,
    ComplianceAgentWorkflowService,
    build_report_generation_recommendation,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class ReportQueryRequest(BaseModel):
    """Single-question report query request."""

    query: str = Field(..., min_length=5, max_length=1000)


class QuestionnaireAssistRequest(BaseModel):
    """Request model for questionnaire assist."""

    questions: List[str] = Field(..., min_length=1, max_length=20)


class QuestionnaireAssistArtifactResponse(BaseModel):
    """Artifact recommendation for a drafted answer."""

    template_key: str
    reason: str


class QuestionnaireAssistControlResponse(BaseModel):
    """Supporting criterion for a drafted answer."""

    id: str
    title: str
    status: str
    open_findings: int
    evidence_items: int


class QuestionnaireAssistSignalResponse(BaseModel):
    """Supporting signal for a drafted answer."""

    id: str
    title: str
    source_label: Optional[str] = None
    status: Optional[str] = None
    href: Optional[str] = None


class QuestionnaireAssistAnswerResponse(BaseModel):
    """Drafted answer entry."""

    question: str
    category: str
    confidence: str
    answer: str
    recommended_artifacts: List[QuestionnaireAssistArtifactResponse]
    supporting_controls: List[QuestionnaireAssistControlResponse]
    supporting_signals: List[QuestionnaireAssistSignalResponse]
    follow_up: List[str]


class QuestionnaireAssistSummaryResponse(BaseModel):
    """Summary of questionnaire-assist results."""

    question_count: int
    overall_score: int
    criteria_ready: int
    criteria_needing_attention: int
    mapped_detections: int
    control_checks: int
    evidence_items: int
    recommended_artifacts: List[QuestionnaireAssistArtifactResponse]


class QuestionnaireAssistResponse(BaseModel):
    """Response model for questionnaire assist."""

    summary: QuestionnaireAssistSummaryResponse
    answers: List[QuestionnaireAssistAnswerResponse]
    suggested_questions: List[str]


class SecurityReviewTemplateResponse(BaseModel):
    """Security review response template."""

    key: str
    title: str
    audience: str
    use_when: str
    subject: str
    body: str
    recommended_artifacts: List[QuestionnaireAssistArtifactResponse]
    talking_points: List[str]
    follow_up: List[str]


class SecurityReviewTemplatesSummaryResponse(BaseModel):
    """Summary block for sales-ready response templates."""

    overall_score: int
    criteria_ready: int
    criteria_needing_attention: int
    mapped_detections: int
    control_checks: int
    evidence_items: int
    framework_pack_states: dict[str, str]


class SecurityReviewTemplatesResponse(BaseModel):
    """Response model for security review templates."""

    summary: SecurityReviewTemplatesSummaryResponse
    templates: List[SecurityReviewTemplateResponse]


def get_report_service() -> ReportGeneratorService:
    """Dependency to get report generator service."""
    return ReportGeneratorService()


def get_questionnaire_assist_service() -> QuestionnaireAssistService:
    """Dependency to get questionnaire-assist service."""
    return QuestionnaireAssistService()


def get_ai_governance_reporting_service() -> AiGovernanceReportingService:
    """Dependency to get AI governance reporting service."""
    return AiGovernanceReportingService()


def get_compliance_agent_workflow_service() -> ComplianceAgentWorkflowService:
    """Dependency to create supervised Compliance Agent recommendations."""
    return ComplianceAgentWorkflowService(
        repository=ComplianceAgentRecommendationRepository(),
        runtime_client=ComplianceAgentRuntimeClient(
            runtime_url=settings.AGENT_RUNTIME_URL,
            internal_token=settings.INTERNAL_SERVICE_TOKEN,
            timeout_seconds=settings.COMPLIANCE_AGENT_TRIGGER_TIMEOUT_SECONDS,
        ),
        enabled=settings.COMPLIANCE_AGENT_ENABLED,
    )


def resolve_accessible_template(
    request: ReportGenerateRequest,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
) -> ReportTemplate:
    """Load a report template while preserving access to shared system templates."""
    template = db.query(ReportTemplate).filter(
        ReportTemplate.id == request.template_id
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {request.template_id} not found",
        )

    if template.tenant_id and template.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Template not accessible for this tenant",
        )

    return template


def _template_key(template_name: str) -> str:
    return (
        (template_name or "")
        .strip()
        .lower()
        .replace("&", "and")
        .replace(" ", "_")
        .replace("-", "_")
    )


def _report_parameters(request: ReportGenerateRequest) -> dict[str, Any]:
    parameters = dict(request.parameters or {})
    explicit_inputs = {
        "framework_ids": request.framework_ids or [],
        "control_ids": request.control_ids or [],
        "evidence_package_ids": request.evidence_package_ids or [],
        "include_gaps": request.include_gaps,
        "include_expired_evidence": request.include_expired_evidence,
    }
    parameters.update(explicit_inputs)
    return parameters


def _report_status_value(report: Report) -> str:
    value = getattr(report, "status", "")
    if hasattr(value, "value"):
        return str(value.value).lower()
    return str(value).lower()


async def _trigger_report_generation_recommendation(
    *,
    workflow_service: ComplianceAgentWorkflowService,
    db: Session,
    tenant_id: str,
    actor_user_id: str,
    authorization: str | None,
    report: Report,
    template: ReportTemplate,
) -> None:
    report_payload = {
        "id": report.id,
        "template_id": template.id,
        "template_name": template.name,
        "report_inputs": (report.report_metadata or {}).get("report_inputs", {}),
    }
    recommendation = build_report_generation_recommendation(report_payload)
    try:
        await workflow_service.create_recommendation_and_task(
            db,
            tenant_id=tenant_id,
            created_by=actor_user_id,
            authorization=authorization,
            metadata={"report": report_payload},
            **recommendation,
        )
    except Exception as exc:  # pragma: no cover - recommendation triggers are side effects.
        logger.warning(
            "Failed to trigger Compliance Agent report recommendation for tenant %s report %s: %s",
            tenant_id,
            report.id,
            exc,
        )


@router.post("/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    request: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    template: ReportTemplate = Depends(resolve_accessible_template),
    tenant_id: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    realm_name: Optional[str] = Header(default="unknown", alias="X-Realm"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_tenant_session),
    service: ReportGeneratorService = Depends(get_report_service),
    workflow_service: ComplianceAgentWorkflowService = Depends(get_compliance_agent_workflow_service),
):
    """
    Generate a report on-demand.
    
    This endpoint creates a report record and generates it in the background.
    """
    try:
        enforce_template_roles(template, token_payload)
        actor_user_id = actor_id_from_payload(token_payload)

        # Create report record
        # Normalize format to enum (case-insensitive to tolerate older callers)
        requested_format = request.format.upper() if request.format else ReportFormat.PDF.value
        if requested_format not in {ReportFormat.PDF.value, ReportFormat.CSV.value}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported report format. Supported formats: pdf, csv",
            )
        report_parameters = _report_parameters(request)
        report = Report(
            tenant_id=tenant_id,
            template_id=request.template_id,
            name=f"{template.name} - {request.date_range.get('start', '') if request.date_range else 'All Time'}",
            format=ReportFormat(requested_format),
            status=ReportStatus.PENDING,
            generated_by=actor_user_id,
            report_metadata={
                "report_type": template.type,
                "template_name": template.name,
                "template_key": _template_key(template.name),
                "report_inputs": {
                    **report_parameters,
                    "date_range": request.date_range or {},
                    "sections": request.sections or [],
                },
                "compliance_snapshot": {"status": "pending"},
            },
        )
        
        if request.date_range:
            from datetime import datetime
            if request.date_range.get('start'):
                report.date_range_start = datetime.fromisoformat(request.date_range['start'].replace('Z', '+00:00'))
            if request.date_range.get('end'):
                report.date_range_end = datetime.fromisoformat(request.date_range['end'].replace('Z', '+00:00'))
        
        db.add(report)
        db.commit()
        db.refresh(report)

        await audit_report_event(
            action="report_generation_requested",
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            resource_type="report",
            resource_id=report.id,
            resource_name=report.name,
            metadata={
                "template_id": template.id,
                "template_name": template.name,
                "format": requested_format,
                "report_inputs": report.report_metadata.get("report_inputs", {}),
            },
        )

        await _trigger_report_generation_recommendation(
            workflow_service=workflow_service,
            db=db,
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            authorization=authorization,
            report=report,
            template=template,
        )
        
        # Generate report in background
        background_tasks.add_task(
            service.generate_report,
            db,
            report,
            template,
            tenant_id,
            realm_name or "unknown",
            request.date_range,
            request.sections,
            report_parameters,
        )
        
        return ReportResponse.model_validate(report)
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create report: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create report: {str(e)}"
        )


@router.post("/query")
async def query_reports(
    request: ReportQueryRequest,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
    service: QuestionnaireAssistService = Depends(get_questionnaire_assist_service),
):
    """Answer a single trust or compliance question using the questionnaire-assist engine."""
    try:
        result = await service.build_questionnaire_assist(tenant_id, [request.query])
        answer = result["answers"][0]
        artifact_keys = [artifact["template_key"] for artifact in answer.get("recommended_artifacts", [])]

        supporting_reports = []
        if artifact_keys:
            reports = (
                db.query(Report)
                .filter(
                    Report.tenant_id == tenant_id,
                    Report.status == ReportStatus.COMPLETED,
                )
                .order_by(Report.generated_at.desc())
                .all()
            )

            for report in reports:
                metadata = report.report_metadata or {}
                template_key = metadata.get("template_key")
                if template_key in artifact_keys:
                    supporting_reports.append(
                        {
                            "report_id": report.id,
                            "report_type": template_key,
                            "generated_at": report.generated_at.isoformat() if report.generated_at else None,
                            "relevance_score": 0.8,
                        }
                    )
                if len(supporting_reports) >= 3:
                    break

        return {
            "query": request.query,
            "answer": answer["answer"],
            "sources": supporting_reports,
            "confidence": answer["confidence"],
            "recommended_artifacts": answer["recommended_artifacts"],
            "follow_up": answer["follow_up"],
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to build questionnaire answer: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Failed to query reports: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query reports: {str(e)}",
        )


@router.post("/questionnaire-assist", response_model=QuestionnaireAssistResponse)
async def questionnaire_assist(
    request: QuestionnaireAssistRequest,
    tenant_id: str = Depends(get_current_tenant),
    service: QuestionnaireAssistService = Depends(get_questionnaire_assist_service),
):
    """Draft answers for a set of customer security-review or audit questionnaire prompts."""
    try:
        return await service.build_questionnaire_assist(tenant_id, request.questions)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to build questionnaire answers: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Failed to build questionnaire assist: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build questionnaire assist: {str(e)}",
        )


@router.get("/security-review-templates", response_model=SecurityReviewTemplatesResponse)
async def security_review_templates(
    tenant_id: str = Depends(get_current_tenant),
    service: QuestionnaireAssistService = Depends(get_questionnaire_assist_service),
):
    """Generate sales-ready security review response templates from the live trust workflow."""
    try:
        return await service.build_security_review_templates(tenant_id)
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to build security review templates: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Failed to build security review templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build security review templates: {str(e)}",
        )


@router.get("/ai-governance/summary")
async def ai_governance_summary(
    lookback_days: int = 30,
    tenant_id: str = Depends(get_current_tenant),
    service: AiGovernanceReportingService = Depends(get_ai_governance_reporting_service),
):
    """Return leadership-facing AI governance and usage reporting."""
    try:
        return await service.build_summary(tenant_id, lookback_days=lookback_days)
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to build AI governance summary: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Failed to build AI governance summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build AI governance summary: {str(e)}",
        )


@router.get("/", response_model=List[ReportResponse])
async def list_reports(
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None,
    report_type: Optional[str] = None,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """List reports for the current tenant."""
    query = db.query(Report).filter(Report.tenant_id == tenant_id)
    
    if status_filter:
        try:
            status_enum = ReportStatus(status_filter)
            query = query.filter(Report.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            )
    if report_type:
        query = query.filter(
            func.lower(Report.report_metadata["report_type"].astext) == report_type.lower()
        )
    
    reports = query.order_by(Report.created_at.desc()).limit(limit).offset(offset).all()
    return [ReportResponse.model_validate(r) for r in reports]


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Get a specific report."""
    report = db.query(Report).filter(
        and_(Report.id == report_id, Report.tenant_id == tenant_id)
    ).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found"
        )
    
    return ReportResponse.model_validate(report)


@router.get("/{report_id}/download")
async def get_report_download(
    report_id: str,
    tenant_id: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    db: Session = Depends(get_tenant_session),
):
    """Return a report download URL and audit the download request."""
    report = db.query(Report).filter(
        and_(Report.id == report_id, Report.tenant_id == tenant_id)
    ).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )

    enforce_report_template_roles(db, report, token_payload)

    if _report_status_value(report) != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report is not ready yet",
        )
    if not report.download_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report download URL not available",
        )

    actor_user_id = actor_id_from_payload(token_payload)
    await audit_report_event(
        action="report_download_requested",
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        resource_type="report",
        resource_id=report.id,
        resource_name=report.name,
        metadata={
            "template_id": report.template_id,
            "format": report.format.value if hasattr(report.format, "value") else str(report.format),
            "has_download_url": bool(report.download_url),
        },
    )

    return {
        "report_id": report.id,
        "report_name": report.name,
        "download_url": report.download_url,
        "format": report.format.value if hasattr(report.format, "value") else str(report.format),
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
    }


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Delete a report."""
    report = db.query(Report).filter(
        and_(Report.id == report_id, Report.tenant_id == tenant_id)
    ).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found"
        )
    
    # Delete file if exists
    if report.file_path:
        try:
            import os
            if os.path.exists(report.file_path):
                os.remove(report.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete report file {report.file_path}: {e}")
    
    db.delete(report)
    db.commit()
    
    return None
