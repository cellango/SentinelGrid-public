"""AI Automation API endpoints (Automated Responses, Remediation, Predictive Analytics, Workflow Integration)."""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.api.request_context import RequestContext, get_current_request_context
from app.models.automation import (
    AutomatedResponseRequest,
    AutomatedResponseResponse,
    RemediationRequest,
    RemediationResponse,
    PredictiveAnalyticsRequest,
    PredictiveAnalyticsResponse,
    WorkflowTriggerRequest,
    WorkflowTriggerResponse
)
from app.services.keycloak_client import KeycloakClient
from app.services.automated_responses import AutomatedResponseService
from app.services.auto_remediation import AutoRemediationService
from app.services.predictive_analytics import PredictiveAnalyticsService
from app.services.workflow_integration import WorkflowIntegrationService
from app.api.auth import get_keycloak_client

router = APIRouter(prefix="/internal/iam/automation", tags=["automation"])


def _resolve_tenant_id(
    request_context: RequestContext,
    requested_tenant_id: Optional[str] = None,
) -> str:
    authenticated_tenant_id = str(request_context.tenant_id)
    if requested_tenant_id is not None and requested_tenant_id != authenticated_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied: Tenant mismatch")
    return authenticated_tenant_id


def get_automated_response_service(
    keycloak_client: KeycloakClient = Depends(get_keycloak_client)
) -> AutomatedResponseService:
    """Get automated response service instance."""
    return AutomatedResponseService(keycloak_client)


def get_remediation_service(
    keycloak_client: KeycloakClient = Depends(get_keycloak_client)
) -> AutoRemediationService:
    """Get auto-remediation service instance."""
    return AutoRemediationService(keycloak_client)


def get_predictive_service() -> PredictiveAnalyticsService:
    """Get predictive analytics service instance."""
    return PredictiveAnalyticsService()


def get_workflow_service() -> WorkflowIntegrationService:
    """Get workflow integration service instance."""
    return WorkflowIntegrationService()


@router.post("/risk-response", response_model=AutomatedResponseResponse)
async def automated_risk_response(
    request: AutomatedResponseRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    response_service: AutomatedResponseService = Depends(get_automated_response_service)
) -> AutomatedResponseResponse:
    """Process automated risk response."""
    try:
        result = response_service.process_risk_response(
            request.user_id,
            request.risk_score,
            request.risk_level,
            request.anomalies,
            _resolve_tenant_id(request_context, request.tenant_id),
            request.auto_remediate
        )
        return AutomatedResponseResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing risk response: {str(e)}")


@router.post("/revoke-suspicious-access")
async def revoke_suspicious_access(
    user_id: str,
    anomalies: List[Dict[str, Any]],
    tenant_id: Optional[str] = Query(None),
    dry_run: bool = Query(False),
    request_context: RequestContext = Depends(get_current_request_context),
    response_service: AutomatedResponseService = Depends(get_automated_response_service)
) -> Dict[str, Any]:
    """Automatically revoke suspicious access."""
    try:
        result = response_service.auto_revoke_suspicious_access(
            user_id,
            anomalies,
            _resolve_tenant_id(request_context, tenant_id),
            dry_run
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error revoking access: {str(e)}")


@router.post("/remediate", response_model=RemediationResponse)
async def auto_remediate(
    request: RemediationRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    remediation_service: AutoRemediationService = Depends(get_remediation_service)
) -> RemediationResponse:
    """Automatically remediate policy violations."""
    try:
        tenant_id = _resolve_tenant_id(request_context, request.tenant_id)
        if request.violation_type == "policy_violations":
            result = remediation_service.remediate_policy_violations(
                request.violations,
                tenant_id,
                request.dry_run
            )
        elif request.violation_type == "stale_access":
            # Special handling for stale access cleanup
            threshold_days = request.violations[0].get("threshold_days", 90) if request.violations else 90
            result = remediation_service.cleanup_stale_access(
                threshold_days,
                tenant_id,
                request.dry_run
            )
        elif request.violation_type == "compliance_issues":
            result = remediation_service.remediate_compliance_issues(
                request.violations,
                tenant_id,
                request.dry_run
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown violation type: {request.violation_type}")
        
        return RemediationResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during remediation: {str(e)}")


@router.post("/predict", response_model=PredictiveAnalyticsResponse)
async def predict(
    request: PredictiveAnalyticsRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    predictive_service: PredictiveAnalyticsService = Depends(get_predictive_service)
) -> PredictiveAnalyticsResponse:
    """Generate predictions using predictive analytics."""
    try:
        _resolve_tenant_id(request_context, request.tenant_id)
        if request.prediction_type == "access_patterns" and request.user_id:
            access_history = request.data.get("access_history", []) if request.data else []
            result = predictive_service.predict_access_patterns(
                request.user_id,
                access_history,
                request.forecast_days
            )
        
        elif request.prediction_type == "risk_trends":
            risk_history = request.data.get("risk_history", []) if request.data else []
            result = predictive_service.forecast_risk_trends(
                risk_history,
                request.forecast_days
            )
        
        elif request.prediction_type == "access_requests":
            request_history = request.data.get("request_history", []) if request.data else []
            result = predictive_service.predict_access_requests(
                request_history,
                request.forecast_days
            )
        
        elif request.prediction_type == "churn_risk" and request.user_id:
            user_data = request.data.get("user_data", {}) if request.data else {}
            access_history = request.data.get("access_history", []) if request.data else []
            result = predictive_service.predict_user_churn_risk(
                request.user_id,
                user_data,
                access_history
            )
        
        else:
            raise HTTPException(status_code=400, detail="Invalid prediction type or missing required data")
        
        return PredictiveAnalyticsResponse(
            prediction_type=request.prediction_type,
            predictions=result,
            confidence=result.get("confidence"),
            generated_at=result.get("generated_at", datetime.utcnow().isoformat())
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating prediction: {str(e)}")


@router.post("/workflow/trigger", response_model=WorkflowTriggerResponse)
async def trigger_workflow(
    request: WorkflowTriggerRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    workflow_service: WorkflowIntegrationService = Depends(get_workflow_service)
) -> WorkflowTriggerResponse:
    """Trigger a workflow (SOAR playbook, approval workflow, etc.)."""
    try:
        tenant_id = _resolve_tenant_id(request_context, request.tenant_id)
        if request.workflow_type == "soar_playbook":
            result = workflow_service.trigger_soar_playbook(
                request.workflow_id,
                request.data,
                tenant_id
            )
        
        elif request.workflow_type == "approval_workflow":
            result = workflow_service.create_automated_approval_workflow(
                request.workflow_id,
                request.data,
                request.data.get("approval_rules", []),
                tenant_id
            )
        
        elif request.workflow_type == "remediation_workflow":
            result = workflow_service.execute_remediation_workflow(
                request.workflow_id,
                request.data,
                request.data.get("remediation_steps", []),
                tenant_id
            )
        
        elif request.workflow_type == "risk_response":
            result = workflow_service.create_risk_response_playbook(
                request.data.get("risk_level", "medium"),
                request.data.get("user_id"),
                request.data,
                tenant_id
            )
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown workflow type: {request.workflow_type}")
        
        return WorkflowTriggerResponse(
            workflow_type=request.workflow_type,
            workflow_id=request.workflow_id,
            execution_id=result.get("execution_id") or result.get("id"),
            status=result.get("status", "triggered"),
            result=result,
            triggered_at=result.get("triggered_at") or datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error triggering workflow: {str(e)}")


@router.get("/workflow/{execution_id}/status")
async def get_workflow_status(
    execution_id: str,
    request_context: RequestContext = Depends(get_current_request_context),
    workflow_service: WorkflowIntegrationService = Depends(get_workflow_service)
) -> Dict[str, Any]:
    """Get status of a workflow execution."""
    try:
        result = workflow_service.get_workflow_status(execution_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting workflow status: {str(e)}")
