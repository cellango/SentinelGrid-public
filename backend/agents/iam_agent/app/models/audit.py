"""Models for audit and accountability features."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AuditEventType(str, Enum):
    """Audit event types."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    USER_MANAGEMENT = "user_management"
    ROLE_MANAGEMENT = "role_management"
    POLICY_MANAGEMENT = "policy_management"
    ACCESS_REQUEST = "access_request"
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    CONFIGURATION_CHANGE = "configuration_change"
    COMPLIANCE_ACTION = "compliance_action"
    REMEDIATION = "remediation"
    RISK_RESPONSE = "risk_response"


class AuditSeverity(str, Enum):
    """Audit severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditEventRequest(BaseModel):
    """Request to log an audit event."""
    event_type: AuditEventType
    actor_id: str
    action: str
    target_resource: Optional[str] = None
    target_user: Optional[str] = None
    outcome: str = "success"
    severity: AuditSeverity = AuditSeverity.MEDIUM
    details: Optional[Dict[str, Any]] = None
    tenant_id: Optional[str] = None


class AuditEventResponse(BaseModel):
    """Response from audit event logging."""
    event_id: str
    event_type: str
    timestamp: datetime
    actor: Dict[str, Any]
    action: str
    outcome: str
    severity: str


class AuditLogQuery(BaseModel):
    """Query parameters for audit logs."""
    tenant_id: Optional[str] = None
    event_types: Optional[List[AuditEventType]] = None
    actor_id: Optional[str] = None
    target_user: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    severity: Optional[AuditSeverity] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class AuditLogResponse(BaseModel):
    """Response with audit logs."""
    logs: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int
    filters: Dict[str, Any]


class AuditReviewRequest(BaseModel):
    """Request to create an audit review."""
    review_name: str
    scope: Dict[str, Any]
    reviewer_id: str
    tenant_id: Optional[str] = None
    due_date: Optional[datetime] = None


class AuditReviewResponse(BaseModel):
    """Response with audit review."""
    review_id: str
    review_name: str
    status: str
    created_at: datetime
    due_date: Optional[datetime] = None


class AuditAnalysisResponse(BaseModel):
    """Response with audit analysis."""
    tenant_id: Optional[str] = None
    analysis_period: Dict[str, str]
    total_events: int
    patterns: Dict[str, Any]
    generated_at: datetime

