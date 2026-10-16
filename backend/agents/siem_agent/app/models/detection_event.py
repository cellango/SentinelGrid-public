"""Detection event data models for SIEM alarms."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class SGContext(BaseModel):
    """SentinelGrid context fields - required for all events."""
    tenant_id: str = Field(..., description="Tenant UUID from Keycloak")
    realm: str = Field(..., description="Keycloak realm")
    alert_type: str = Field(..., description="Alert type identifier")
    playbook_id: Optional[str] = Field(None, description="Target playbook ID")
    severity: str = Field(..., description="Alert severity: critical, high, medium, low")
    category: str = Field(..., description="Alert category: identity, email, endpoint, etc.")


class RuleInfo(BaseModel):
    """Detection rule information."""
    id: str = Field(..., description="Rule ID (e.g., SG-DET-001)")
    name: str = Field(..., description="Rule name")
    version: str = Field(default="1.0.0", description="Rule version")


class UserInfo(BaseModel):
    """User information from event."""
    id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None


class SourceInfo(BaseModel):
    """Source information (IP, geo, etc.)."""
    ip: Optional[str] = None
    geo: Optional[Dict[str, Any]] = None
    port: Optional[int] = None


class HostInfo(BaseModel):
    """Host information."""
    name: Optional[str] = None
    id: Optional[str] = None
    ip: Optional[str] = None
    asset_criticality: Optional[str] = None


class DeviceInfo(BaseModel):
    """Device information."""
    id: Optional[str] = None
    platform: Optional[str] = None
    owner_user_id: Optional[str] = None
    owner_email: Optional[str] = None
    status: Optional[str] = None


class MalwareInfo(BaseModel):
    """Malware information."""
    name: Optional[str] = None
    family: Optional[str] = None
    hash: Optional[str] = None


class EmailInfo(BaseModel):
    """Email information."""
    message_id: Optional[str] = None
    subject: Optional[str] = None
    from_address: Optional[str] = Field(None, alias="from")
    to: Optional[List[str]] = None


class CloudInfo(BaseModel):
    """Cloud provider information."""
    provider: Optional[str] = None
    account_id: Optional[str] = None
    region: Optional[str] = None


class ResourceInfo(BaseModel):
    """Cloud resource information."""
    type: Optional[str] = None
    id: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None


class IAMInfo(BaseModel):
    """IAM action information."""
    action: Optional[str] = None
    role_name: Optional[str] = None


class NetworkInfo(BaseModel):
    """Network transfer information."""
    bytes_out: Optional[int] = None
    bytes_out_1h: Optional[int] = None
    approx_gb: Optional[float] = None


class AuthInfo(BaseModel):
    """Authentication information."""
    failed_count_10m: Optional[int] = None
    first_failure_at: Optional[str] = None
    success_at: Optional[str] = None
    method: Optional[str] = None


class SprayInfo(BaseModel):
    """Password spray information."""
    failed_attempts_10m: Optional[int] = None
    distinct_users: Optional[int] = None


class CampaignInfo(BaseModel):
    """Email campaign information."""
    subject_pattern: Optional[str] = None
    approx_recipients: Optional[int] = None


class DetectionEvent(BaseModel):
    """
    Detection event model - normalized format for all SIEM alarms.
    
    This model represents a detection event created by OpenSearch monitors
    that will trigger incident creation in the SOAR platform.
    """
    
    # Core fields
    timestamp: datetime = Field(default_factory=datetime.utcnow, alias="@timestamp")
    event_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique event ID")
    
    # SentinelGrid context (required)
    sg: SGContext
    
    # Rule information
    rule: RuleInfo
    
    # Entity information (optional, depends on alert type)
    user: Optional[UserInfo] = None
    source: Optional[SourceInfo] = None
    host: Optional[HostInfo] = None
    device: Optional[DeviceInfo] = None
    malware: Optional[MalwareInfo] = None
    email: Optional[EmailInfo] = None
    cloud: Optional[CloudInfo] = None
    resource: Optional[ResourceInfo] = None
    iam: Optional[IAMInfo] = None
    network: Optional[NetworkInfo] = None
    auth: Optional[AuthInfo] = None
    spray: Optional[SprayInfo] = None
    campaign: Optional[CampaignInfo] = None
    
    # Additional context
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    raw_alert: Optional[Dict[str, Any]] = None  # Original alert from OpenSearch
    
    # Actor information (who reported/triggered)
    actor: Optional[Dict[str, Any]] = None
    target_user: Optional[UserInfo] = None
    report_source: Optional[str] = None
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "@timestamp": "2025-12-02T12:00:05Z",
                "event_id": "550e8400-e29b-41d4-a716-446655440000",
                "sg": {
                    "tenant_id": "tenant-123",
                    "realm": "sentinelgrid",
                    "alert_type": "suspicious_login",
                    "playbook_id": "PLAYBOOK_ACCOUNT_TAKEOVER",
                    "severity": "high",
                    "category": "identity"
                },
                "rule": {
                    "id": "SG-DET-001-SUSPICIOUS-LOGIN",
                    "name": "Suspicious login: failures then success",
                    "version": "1.0.0"
                },
                "user": {
                    "id": "user-42",
                    "email": "jane.doe@example.com"
                },
                "source": {
                    "ip": "203.0.113.10",
                    "geo": {"country": "US"}
                },
                "auth": {
                    "failed_count_10m": 7,
                    "first_failure_at": "2025-12-02T11:52:00Z",
                    "success_at": "2025-12-02T11:59:30Z"
                }
            }
        }


class DetectionEventCreate(BaseModel):
    """Model for creating detection events via API."""
    sg: SGContext
    rule: RuleInfo
    user: Optional[UserInfo] = None
    source: Optional[SourceInfo] = None
    host: Optional[HostInfo] = None
    device: Optional[DeviceInfo] = None
    malware: Optional[MalwareInfo] = None
    email: Optional[EmailInfo] = None
    cloud: Optional[CloudInfo] = None
    resource: Optional[ResourceInfo] = None
    iam: Optional[IAMInfo] = None
    network: Optional[NetworkInfo] = None
    auth: Optional[AuthInfo] = None
    spray: Optional[SprayInfo] = None
    campaign: Optional[CampaignInfo] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    raw_alert: Optional[Dict[str, Any]] = None
    actor: Optional[Dict[str, Any]] = None
    target_user: Optional[UserInfo] = None
    report_source: Optional[str] = None


class DetectionEventResponse(BaseModel):
    """Response model for detection event operations."""
    event_id: str
    indexed: bool
    index_name: str
    incident_id: Optional[UUID] = None
    message: str

