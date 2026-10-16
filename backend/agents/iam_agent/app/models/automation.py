"""Models for AI automation features."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class AutomatedResponseRequest(BaseModel):
    """Request for automated risk response."""
    user_id: str
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: str = Field(..., description="low, medium, high, or critical")
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    tenant_id: Optional[str] = None
    auto_remediate: bool = Field(False, description="If true, execute remediation")


class AutomatedResponseResponse(BaseModel):
    """Response from automated risk response."""
    user_id: str
    tenant_id: Optional[str] = None
    risk_score: float
    risk_level: str
    actions_taken: List[Dict[str, Any]] = Field(default_factory=list)
    anomalies_count: int
    critical_anomalies_count: int
    processed_at: datetime
    auto_remediated: bool


class RemediationRequest(BaseModel):
    """Request for auto-remediation."""
    violation_type: str = Field(..., description="over_privileged, policy_violation, expired_entitlement, unused_entitlement, etc.")
    violations: List[Dict[str, Any]] = Field(..., description="List of violations to remediate")
    tenant_id: Optional[str] = None
    dry_run: bool = Field(False, description="If true, simulate remediation without executing")


class RemediationResponse(BaseModel):
    """Response from auto-remediation."""
    tenant_id: Optional[str] = None
    total_violations: int
    remediated: int
    failed: int
    dry_run: bool
    results: List[Dict[str, Any]] = Field(default_factory=list)
    processed_at: datetime


class PredictiveAnalyticsRequest(BaseModel):
    """Request for predictive analytics."""
    prediction_type: str = Field(..., description="access_patterns, risk_trends, access_requests, churn_risk")
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    forecast_days: int = Field(30, ge=1, le=365)
    data: Optional[Dict[str, Any]] = None


class PredictiveAnalyticsResponse(BaseModel):
    """Response from predictive analytics."""
    prediction_type: str
    predictions: Dict[str, Any] = Field(default_factory=dict)
    confidence: Optional[float] = None
    generated_at: datetime


class WorkflowTriggerRequest(BaseModel):
    """Request to trigger a workflow."""
    workflow_type: str = Field(..., description="soar_playbook, approval_workflow, remediation_workflow")
    workflow_id: str
    data: Dict[str, Any] = Field(..., description="Workflow-specific data")
    tenant_id: Optional[str] = None
    auto_execute: bool = Field(False, description="If true, execute workflow immediately")


class WorkflowTriggerResponse(BaseModel):
    """Response from workflow trigger."""
    workflow_type: str
    workflow_id: str
    execution_id: Optional[str] = None
    status: str
    result: Optional[Dict[str, Any]] = None
    triggered_at: datetime

