"""Tenant models for provisioning."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class TenantProvisionRequest(BaseModel):
    """Request model for tenant provisioning."""
    company_name: str = Field(..., min_length=2, max_length=255)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8, max_length=100)
    admin_first_name: Optional[str] = Field(None, max_length=100)
    admin_last_name: Optional[str] = Field(None, max_length=100)
    idp_mode: str = Field(default="sentinelgrid", pattern="^(sentinelgrid|existing_sso)$")
    
    @field_validator('company_name')
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        """Validate and sanitize company name."""
        # Remove special characters, convert to lowercase for slug
        return v.strip()
    
    @property
    def slug(self) -> str:
        """Generate slug from company name."""
        slug = re.sub(r'[^a-z0-9]+', '-', self.company_name.lower())
        slug = slug.strip('-')
        return slug


class TenantProvisionResponse(BaseModel):
    """Response model for tenant provisioning."""
    tenant_id: UUID
    realm_name: str
    company_name: str
    admin_username: str
    admin_email: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class TenantStatus(BaseModel):
    """Tenant status information."""
    tenant_id: UUID
    company_name: str
    realm_name: str
    status: str
    created_at: datetime
    admin_email: str


class IntegrationStatus(BaseModel):
    """Integration status for a tenant."""
    identity_provider: Optional[dict] = None
    cloud_provider: Optional[dict] = None


class IdentityProviderStatus(BaseModel):
    """Identity provider connection status."""
    provider: str  # google_workspace, microsoft_entra, okta, sentinelgrid
    status: str  # connected, not_connected, error
    last_sync: Optional[datetime] = None
    users_count: Optional[int] = None
    error_message: Optional[str] = None


class CloudProviderStatus(BaseModel):
    """Cloud provider connection status."""
    provider: str  # aws, azure, gcp
    status: str  # connected, not_connected, error
    last_events: Optional[datetime] = None
    events_ingested: Optional[int] = None
    error_message: Optional[str] = None


class AlertPreferencesRequest(BaseModel):
    """Request model for alert preferences."""
    email_notifications: dict = Field(..., description="Notification preferences by severity")
    notification_email: EmailStr = Field(..., description="Email address for notifications")


class AlertPreferencesResponse(BaseModel):
    """Response model for alert preferences."""
    tenant_id: UUID
    email_notifications: dict
    notification_email: str
    updated_at: datetime


class FeatureFlagsRequest(BaseModel):
    """Request model for tenant feature flags."""
    edr_openedr_enabled: bool = True
    edr_velociraptor_enabled: bool = False


class FeatureFlagsResponse(BaseModel):
    """Response model for tenant feature flags."""
    tenant_id: UUID
    edr_openedr_enabled: bool
    edr_velociraptor_enabled: bool
    updated_at: datetime


class UserInvitationRequest(BaseModel):
    """Request model for user invitations."""
    emails: list[EmailStr] = Field(..., min_length=1, description="List of email addresses to invite")
    role: str = Field(default="soc_analyst", description="Role to assign to invited users")


class UserInvitationResponse(BaseModel):
    """Response model for user invitation."""
    tenant_id: UUID
    invitations_sent: int
    invitations: list[dict]
    created_at: datetime
