"""Event models for ingestion."""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict


class RawEvent(BaseModel):
    """Raw event from connector before normalization."""
    event_type: str
    source: str  # google_workspace, aws_cloudtrail, etc.
    timestamp: datetime
    raw_data: Dict[str, Any]
    tenant_id: Optional[str] = None  # May be provided by connector
    metadata: Optional[Dict[str, Any]] = None
    edr_source: Optional[str] = None  # Optional hint for endpoint data source
    sidecar_enabled: Optional[bool] = None  # Whether an endpoint sidecar produced the event


class ECSField(BaseModel):
    """ECS (Elastic Common Schema) field structure."""
    model_config = ConfigDict(populate_by_name=True)
    timestamp: datetime = Field(alias="@timestamp")
    tenant_id: str
    event_type: str
    source: Dict[str, Any]
    edr_source: Optional[str] = None
    sidecar_enabled: Optional[bool] = None
    process: Optional[Dict[str, Any]] = None
    registry: Optional[Dict[str, Any]] = None
    file: Optional[Dict[str, Any]] = None
    driver: Optional[Dict[str, Any]] = None
    module: Optional[Dict[str, Any]] = None
    hunt: Optional[Dict[str, Any]] = None
    task: Optional[Dict[str, Any]] = None
    collection: Optional[Dict[str, Any]] = None
    sensor: Optional[Dict[str, Any]] = None
    event: Optional[Dict[str, Any]] = None
    user: Optional[Dict[str, Any]] = None
    host: Optional[Dict[str, Any]] = None
    device: Optional[Dict[str, Any]] = None
    network: Optional[Dict[str, Any]] = None
    action: Optional[str] = None
    outcome: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class IngestEvent(BaseModel):
    """Event to be ingested (normalized to ECS)."""
    ecs_fields: ECSField
    raw_data: Dict[str, Any]  # Original raw data preserved


class IngestBatchRequest(BaseModel):
    """Batch ingestion request."""
    events: List[RawEvent]
    tenant_id: Optional[str] = None  # Override tenant_id if not in events


class IngestResponse(BaseModel):
    """Ingestion response."""
    ingested_count: int
    failed_count: int
    errors: List[str] = Field(default_factory=list)
    batch_id: Optional[str] = None
