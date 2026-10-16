"""Models for sync job management."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class SyncType(str, Enum):
    """Sync types."""
    USERS = "users"
    GROUPS = "groups"
    FULL = "full"


class SyncDirection(str, Enum):
    """Sync directions."""
    IMPORT = "import"
    EXPORT = "export"
    BIDIRECTIONAL = "bidirectional"


class JobSchedule(str, Enum):
    """Schedule types."""
    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class JobStatus(str, Enum):
    """Job status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CreateSyncJobRequest(BaseModel):
    """Request to create a sync job."""
    integration_id: str
    sync_type: SyncType
    direction: SyncDirection = SyncDirection.IMPORT
    filters: Optional[Dict[str, Any]] = None
    tenant_id: Optional[str] = None


class CreateSyncJobResponse(BaseModel):
    """Response from creating a sync job."""
    job_id: str
    integration_id: str
    sync_type: str
    direction: str
    status: str
    created_at: datetime
    tenant_id: Optional[str] = None


class JobStatusResponse(BaseModel):
    """Response with job status."""
    job_id: str
    status: str
    sync_type: str
    direction: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_seconds: Optional[float] = None


class ScheduleSyncJobRequest(BaseModel):
    """Request to schedule a sync job."""
    integration_id: str
    schedule_type: JobSchedule
    sync_type: SyncType
    direction: SyncDirection = SyncDirection.IMPORT
    cron_expression: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    tenant_id: Optional[str] = None


class ScheduleResponse(BaseModel):
    """Response with schedule information."""
    schedule_id: str
    integration_id: str
    schedule_type: str
    sync_type: str
    direction: str
    enabled: bool
    last_run: Optional[datetime] = None
    next_run: datetime
    created_at: datetime
    tenant_id: Optional[str] = None

