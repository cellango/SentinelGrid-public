"""Event models for SIEM Agent."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EventBase(BaseModel):
    """Base event model (ECS-based)."""
    timestamp: datetime = Field(alias="@timestamp")
    tenant_id: str
    event_type: str
    source_name: Optional[str] = None  # google_workspace, aws_cloudtrail, etc.
    action: Optional[str] = None
    user: Optional[Dict[str, Any]] = None
    source: Optional[Dict[str, Any]] = None  # Source IP/location info
    device: Optional[Dict[str, Any]] = None
    details: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True


class Event(EventBase):
    """Event model with ID."""
    id: str
    
    class Config:
        from_attributes = True


class EventSearchRequest(BaseModel):
    """Request model for advanced log search."""
    query: Optional[Dict[str, Any]] = None  # OpenSearch query DSL
    filters: Optional[Dict[str, str]] = None  # Simple filters
    size: int = Field(default=100, ge=1, le=1000)
    from_: int = Field(default=0, ge=0, alias="from")
    sort: Optional[List[Dict[str, str]]] = None
    
    class Config:
        populate_by_name = True


class EventSearchResponse(BaseModel):
    """Response model for log search."""
    events: List[Event]
    total: int
    took_ms: int
    timed_out: bool


class SimpleSearchRequest(BaseModel):
    """Request model for simple keyword search."""
    q: str  # Search query (keywords)
    event_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class EntityTimelineRequest(BaseModel):
    """Request model for entity timeline."""
    entity_type: str = Field(..., pattern="^(user|host|ip|domain|file_hash)$")
    entity_id: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    event_types: Optional[List[str]] = None
    limit: int = Field(default=1000, ge=1, le=10000)


class EntityTimelineResponse(BaseModel):
    """Response model for entity timeline."""
    entity: Dict[str, str]
    time_range: Dict[str, datetime]
    events: List[Event]
    summary: Dict[str, Any]
