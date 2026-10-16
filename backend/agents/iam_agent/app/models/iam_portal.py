"""IAM Portal data models."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# App Models
class AppBase(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    app_type: str
    icon_url: Optional[str] = None
    is_active: bool = True
    config: Optional[Dict[str, Any]] = None


class AppCreate(AppBase):
    pass


class AppUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


class App(AppBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Entitlement Models
class EntitlementBase(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    entitlement_type: str = "role"
    is_privileged: bool = False
    requires_mfa: bool = False
    risk_level: str = "low"


class EntitlementCreate(EntitlementBase):
    app_id: UUID


class EntitlementUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_privileged: Optional[bool] = None
    requires_mfa: Optional[bool] = None
    risk_level: Optional[str] = None


class Entitlement(EntitlementBase):
    id: UUID
    tenant_id: UUID
    app_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Entitlement Mapping Models
class EntitlementMappingBase(BaseModel):
    realm_name: str
    keycloak_group_id: Optional[str] = None
    keycloak_group_name: Optional[str] = None
    keycloak_role_name: Optional[str] = None
    keycloak_client_id: Optional[str] = None
    provisioning_config: Optional[Dict[str, Any]] = None


class EntitlementMappingCreate(EntitlementMappingBase):
    entitlement_id: UUID


class EntitlementMapping(EntitlementMappingBase):
    id: UUID
    entitlement_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Access Profile Models
class AccessProfileBase(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    is_default: bool = False
    is_system: bool = False
    is_birthright: bool = False
    scope: Optional[str] = "all_users"


class AccessProfileCreate(AccessProfileBase):
    entitlement_ids: List[UUID] = []


class AccessProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
    is_birthright: Optional[bool] = None
    scope: Optional[str] = None
    entitlement_ids: Optional[List[UUID]] = None


class AccessProfile(AccessProfileBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    entitlements: List[Entitlement] = []

    class Config:
        from_attributes = True


# User Entitlement Models
class UserEntitlementBase(BaseModel):
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None


class UserEntitlementCreate(UserEntitlementBase):
    user_id: str
    entitlement_id: UUID


class UserEntitlement(UserEntitlementBase):
    id: UUID
    tenant_id: UUID
    user_id: str
    entitlement_id: UUID
    entitlement: Optional[Entitlement] = None
    granted_by: Optional[str] = None
    granted_at: datetime
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Access Request Models
class AccessRequestBase(BaseModel):
    reason: str
    duration_days: Optional[int] = None


class AccessRequestCreate(AccessRequestBase):
    entitlement_id: UUID


class AccessRequestUpdate(BaseModel):
    status: Optional[str] = None
    resolution_notes: Optional[str] = None


class AccessRequest(AccessRequestBase):
    id: UUID
    tenant_id: UUID
    requested_by: str
    entitlement_id: UUID
    entitlement: Optional[Entitlement] = None
    status: str
    requested_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None
    approvals: List["Approval"] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Approval Models
class ApprovalBase(BaseModel):
    approver_type: str
    notes: Optional[str] = None


class ApprovalCreate(ApprovalBase):
    access_request_id: UUID
    approver_id: str


class ApprovalUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class Approval(ApprovalBase):
    id: UUID
    access_request_id: UUID
    approver_id: str
    status: str
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# User Models (for People page)
class UserInfo(BaseModel):
    user_id: str
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    enabled: bool = True
    manager_id: Optional[str] = None
    department: Optional[str] = None
    team: Optional[str] = None
    location: Optional[str] = None
    employee_type: Optional[str] = None
    is_privileged: bool = False
    access_profile_id: Optional[UUID] = None
    tenant_id: Optional[UUID] = None
    entitlements: List[UserEntitlement] = []
    created_at: Optional[datetime] = None
    activate_at: Optional[datetime] = None
    deactivate_at: Optional[datetime] = None


class UserCreate(BaseModel):
    username: str
    email: str
    tenant_id: UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    department: Optional[str] = None
    team: Optional[str] = None
    manager_id: Optional[str] = None
    location: Optional[str] = None
    employee_type: Optional[str] = None
    access_profile_id: Optional[UUID] = None
    make_admin: bool = False
    is_privileged: bool = False


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    team: Optional[str] = None
    manager_id: Optional[str] = None
    location: Optional[str] = None
    employee_type: Optional[str] = None
    enabled: Optional[bool] = None
    access_profile_id: Optional[UUID] = None
    is_privileged: Optional[bool] = None


# My Access Models (for self-service)
class MyAccessSummary(BaseModel):
    current_entitlements: List[UserEntitlement]
    pending_requests: List[AccessRequest]
    available_entitlements: List[Entitlement]


# Policy Models
class Policy(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    display_name: str
    description: Optional[str] = None
    policy_type: str
    scope: str
    scope_id: Optional[UUID] = None
    policy_data: dict
    is_active: bool = True
    priority: int = 100
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    is_template: bool = False
    approval_required: bool = False
    approval_status: Optional[str] = None


class PolicyCreate(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    policy_type: str
    scope: str = "tenant"
    scope_id: Optional[UUID] = None
    policy_data: dict
    is_active: bool = True
    priority: int = 100
    approval_required: bool = False


class PolicyUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    policy_type: Optional[str] = None
    scope: Optional[str] = None
    scope_id: Optional[UUID] = None
    policy_data: Optional[dict] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    approval_required: Optional[bool] = None
    approval_status: Optional[str] = None


# Update forward references
AccessRequest.model_rebuild()
Approval.model_rebuild()
