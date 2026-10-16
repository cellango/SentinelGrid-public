"""AI Features models for IAM Agent."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class AnomalyDetectionRequest(BaseModel):
    """Request for anomaly detection."""
    user_id: Optional[str] = Field(None, description="Specific user ID to analyze")
    tenant_id: Optional[str] = Field(None, description="Tenant ID for multi-tenancy")
    time_window_days: Optional[int] = Field(30, description="Time window for analysis (days)")


class AnomalyResponse(BaseModel):
    """Response from anomaly detection."""
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    anomalies: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class RiskScoreRequest(BaseModel):
    """Request for risk scoring."""
    user_id: Optional[str] = Field(None, description="User ID for user risk score")
    entitlement_id: Optional[str] = Field(None, description="Entitlement ID for entitlement risk")
    resource_id: Optional[str] = Field(None, description="Resource ID for resource risk")
    tenant_id: Optional[str] = Field(None, description="Tenant ID for tenant risk")
    scope: str = Field("user", description="Scope: 'user', 'entitlement', 'resource', or 'tenant'")


class RiskScoreResponse(BaseModel):
    """Response from risk scoring."""
    scope: str
    entity_id: str
    tenant_id: Optional[str] = None
    overall_risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_level: str = Field(..., description="low, medium, high, or critical")
    risk_factors: Dict[str, float] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    calculated_at: datetime = Field(default_factory=datetime.utcnow)


class RecommendationRequest(BaseModel):
    """Request for recommendations."""
    type: Optional[str] = Field(None, description="Type: 'role_mining', 'optimization', 'compliance', 'security', 'ai'")
    tenant_id: Optional[str] = Field(None, description="Tenant ID")
    query: Optional[str] = Field(None, description="Natural language query for AI recommendations")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class RecommendationResponse(BaseModel):
    """Response with recommendations."""
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    total_count: int = 0
    high_priority_count: int = 0
    generated_at: datetime = Field(default_factory=datetime.utcnow)

