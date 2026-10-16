"""Snapshot models."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime


class AlertSummary(BaseModel):
    """Summary of an alert for snapshot."""
    id: str
    title: str
    severity: str
    status: str
    description: Optional[str] = None
    created_at: Optional[str] = None


class SecuritySnapshotSummary(BaseModel):
    """Summary statistics for security snapshot."""
    events_count: int
    alerts_count: int
    users_active: int
    users_total: int = 0


class IAMSummary(BaseModel):
    """IAM statistics summary."""
    users_count: int
    active_users_count: int = 0
    roles_count: int = 0
    groups_count: int = 0


class Recommendation(BaseModel):
    """AI-generated recommendation."""
    priority: str  # High, Medium, Low
    action: str


class AIAnalysis(BaseModel):
    """AI analysis result."""
    posture: str  # Good, Needs Attention, At Risk
    risk_level: str  # Low, Medium, High, Critical
    key_findings: List[str]
    recommendations: List[Recommendation]
    summary: str
    raw_response: Optional[str] = None
    error: Optional[str] = None


class SecuritySnapshot(BaseModel):
    """Complete security snapshot response."""
    tenant_id: str
    generated_at: str
    summary: SecuritySnapshotSummary
    alerts_by_severity: Dict[str, int] = {}
    alerts_by_status: Dict[str, int] = {}
    top_findings: List[AlertSummary]
    iam_summary: IAMSummary
    ai_analysis: AIAnalysis

