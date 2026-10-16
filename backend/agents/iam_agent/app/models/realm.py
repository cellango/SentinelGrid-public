"""Realm creation models."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class RealmType(str, Enum):
    """Realm type enumeration."""
    PLATFORM_ADMIN = "platform_admin"
    MULTI_TENANT = "multi_tenant"
    DEDICATED_CUSTOMER = "dedicated_customer"
    DEMO = "demo"


class RealmCreateRequest(BaseModel):
    """Request to create a new realm."""
    realm_name: str = Field(..., description="Name of the realm (must follow naming conventions)")
    realm_type: RealmType = Field(..., description="Type of realm")
    display_name: Optional[str] = Field(None, description="Display name for the realm (defaults to realm_name)")
    region: Optional[str] = Field(None, description="Region code for multi-tenant realms (e.g., 'us', 'eu')")
    shard_number: Optional[int] = Field(None, description="Shard number for multi-tenant realms (e.g., 1, 2)")
    customer_slug: Optional[str] = Field(None, description="Customer slug for dedicated customer realms")


class RealmCreateResponse(BaseModel):
    """Response from realm creation."""
    realm_name: str
    keycloak_realm_id: str
    status: str = Field(..., description="'created' if new realm, 'exists' if realm already existed")
    user_profile_configured: bool = Field(..., description="Whether User Profile was configured with tenant_id attribute")

