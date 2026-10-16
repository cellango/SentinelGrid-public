"""Alert models for SIEM Agent."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class AlertBase(BaseModel):
    """Base alert model."""
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    status: str = Field(..., pattern="^(open|acknowledged|resolved|false_positive)$")
    title: str
    description: str
    timestamp: datetime
    source: str  # detection_rule_id, manual, external
    detection_rule_id: Optional[str] = None
    user_id: Optional[str] = None
    source_ip: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    count: int = Field(default=1, ge=1)
    first_seen: datetime
    last_seen: datetime
    assigned_to: Optional[str] = None
    comments: Optional[str] = None
    events: List[str] = Field(default_factory=list)  # Linked event IDs for enrichment


class Alert(AlertBase):
    """Alert model with ID and timestamps."""
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """Response model for alert list endpoint."""
    alerts: List[Alert]
    total: int
    limit: int
    offset: int


class AlertCreate(BaseModel):
    """Model for creating alert."""
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    status: str = Field(..., pattern="^(open|acknowledged|resolved|false_positive)$")
    title: str
    description: str
    timestamp: Optional[datetime] = None  # Defaults to now if not provided
    source: str
    detection_rule_id: Optional[str] = None
    user_id: Optional[str] = None
    source_ip: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    count: int = Field(default=1, ge=1)
    first_seen: Optional[datetime] = None  # Defaults to timestamp if not provided
    last_seen: Optional[datetime] = None  # Defaults to timestamp if not provided
    assigned_to: Optional[str] = None
    comments: Optional[str] = None


class AlertUpdate(BaseModel):
    """Model for updating alert."""
    status: Optional[str] = Field(None, pattern="^(open|acknowledged|resolved|false_positive)$")
    assigned_to: Optional[str] = None
    comments: Optional[str] = None

