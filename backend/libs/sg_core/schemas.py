"""Pydantic schemas for API responses and requests."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class AlertResponse(BaseModel):
    """Alert response schema."""
    id: UUID
    tenant_id: UUID
    source: str
    external_id: str
    title: str
    description: Optional[str] = None
    raw_severity: Optional[str] = None
    status: str
    detection_time: datetime
    asset_id: Optional[str] = None
    user_identifier: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None
    nist_controls: Optional[Dict[str, Any]] = None
    mitre_tactics: Optional[Dict[str, Any]] = None
    mitre_techniques: Optional[Dict[str, Any]] = None
    cve_ids: Optional[List[str]] = None
    exploit_indicators: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IncidentResponse(BaseModel):
    """Incident response schema."""
    id: UUID
    tenant_id: UUID
    source: str
    external_id: str
    title: str
    status: str
    severity: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None
    nist_controls: Optional[Dict[str, Any]] = None
    mitre_tactics: Optional[Dict[str, Any]] = None
    mitre_techniques: Optional[Dict[str, Any]] = None
    cve_ids: Optional[List[str]] = None
    exploit_indicators: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TicketAIEnrichmentResponse(BaseModel):
    """AI-generated enrichment data for tickets response schema."""
    id: UUID
    ticket_id: UUID
    enrichment_type: str
    model_name: str
    model_version: str
    content: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PhishingReportResponse(BaseModel):
    """Phishing report response schema."""
    id: UUID
    tenant_id: UUID
    message_id: str
    subject: Optional[str] = None
    from_address: str
    to_address: str
    reply_to: Optional[str] = None
    received_date: datetime
    reported_by: Optional[str] = None
    raw_email: str
    html_body: Optional[str] = None
    text_body: Optional[str] = None
    attachments: Optional[Dict[str, Any]] = None
    classification: Optional[str] = None
    classification_confidence: Optional[float] = None
    classified_by: Optional[str] = None
    classified_at: Optional[datetime] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    ai_summary: Optional[str] = None
    ai_recommended_actions: Optional[Dict[str, Any]] = None
    mitre_tactics: Optional[List[str]] = None
    mitre_techniques: Optional[List[str]] = None
    nist_controls: Optional[List[str]] = None
    status: str
    severity: Optional[str] = None
    assigned_to: Optional[str] = None
    ticket_id: Optional[UUID] = None
    incident_id: Optional[UUID] = None
    similar_emails: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PhishingReportCreate(BaseModel):
    """Schema for creating a phishing report."""
    message_id: str
    subject: Optional[str] = None
    from_address: str
    to_address: str
    reply_to: Optional[str] = None
    received_date: datetime
    reported_by: Optional[str] = None
    raw_email: str
    html_body: Optional[str] = None
    text_body: Optional[str] = None
    attachments: Optional[Dict[str, Any]] = None


class PhishingReportUpdate(BaseModel):
    """Schema for updating a phishing report."""
    classification: Optional[str] = None
    classification_confidence: Optional[float] = None
    classified_by: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
    assigned_to: Optional[str] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    ai_summary: Optional[str] = None
    ai_recommended_actions: Optional[Dict[str, Any]] = None
    mitre_tactics: Optional[List[str]] = None
    mitre_techniques: Optional[List[str]] = None
    nist_controls: Optional[List[str]] = None


class PhishingObservableResponse(BaseModel):
    """Phishing observable response schema."""
    id: UUID
    tenant_id: UUID
    phishing_report_id: UUID
    observable_type: str
    observable_value: str
    observable_context: Optional[str] = None
    threat_intel: Optional[Dict[str, Any]] = None
    reputation_score: Optional[int] = None
    is_malicious: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PhishingObservableCreate(BaseModel):
    """Schema for creating a phishing observable."""
    observable_type: str
    observable_value: str
    observable_context: Optional[str] = None


# ============================================================================
# Hero Flow 4 & 5 - New Schemas
# ============================================================================

class IAMFindingResponse(BaseModel):
    """IAM finding response schema."""
    id: UUID
    tenant_id: UUID
    identity_id: Optional[UUID] = None
    finding_type: str
    severity: str
    description: str
    recommendation: Optional[str] = None
    status: str
    detected_at: datetime
    nist_control_id: Optional[str] = None
    remediation_plan: Optional[Dict[str, Any]] = None
    remediation_status: str
    remediated_at: Optional[datetime] = None
    remediated_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PostureFindingResponse(BaseModel):
    """Posture finding response schema."""
    id: UUID
    tenant_id: UUID
    cloud_account_id: Optional[UUID] = None
    scan_id: Optional[UUID] = None
    check_id: Optional[str] = None
    title: str
    description: str
    severity: str
    resource_id: Optional[str] = None
    service: Optional[str] = None
    category: Optional[str] = None
    framework: Optional[str] = None
    remediation: Optional[str] = None
    status: str
    detected_at: datetime
    nist_control_id: Optional[str] = None
    remediation_plan: Optional[Dict[str, Any]] = None
    remediation_status: str
    remediated_at: Optional[datetime] = None
    remediated_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RemediationMetadataResponse(BaseModel):
    """Remediation metadata response schema."""
    id: UUID
    tenant_id: UUID
    finding_id: UUID
    finding_type: str
    playbook_execution_id: Optional[UUID] = None
    remediation_plan: Optional[Dict[str, Any]] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertPlaybookTriggerResponse(BaseModel):
    """Alert-playbook trigger response schema."""
    id: UUID
    tenant_id: UUID
    alert_id: UUID
    playbook_id: UUID
    playbook_execution_id: Optional[UUID] = None
    trigger_reason: Optional[str] = None
    evaluated_at: datetime
    triggered_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
    threat_intel: Optional[Dict[str, Any]] = None
    reputation_score: Optional[int] = None
    is_malicious: Optional[bool] = False
