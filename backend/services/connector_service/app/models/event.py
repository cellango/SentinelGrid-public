"""Event models for connectors."""

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel


class RawEvent(BaseModel):
    """Raw event from connector before normalization."""
    event_type: str
    source: str  # google_workspace, aws_cloudtrail, etc.
    timestamp: datetime
    raw_data: Dict[str, Any]
    tenant_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

