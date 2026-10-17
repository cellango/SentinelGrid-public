"""IAM Portal API endpoints."""

import logging
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.api.request_context import get_tenant_session, RequestContext, get_current_request_context, ensure_request_has_any_role
from app.api.policies import get_policy_administrator
from app.services.iam_portal_service import IAMPortalService
from app.models.iam_portal import (
    AppCreate, AppUpdate, App,
    EntitlementCreate, EntitlementUpdate, Entitlement,
    EntitlementMappingCreate,
    AccessProfileCreate, AccessProfileUpdate, AccessProfile,
    UserEntitlementCreate, UserEntitlement,
    AccessRequestCreate, AccessRequestUpdate, AccessRequest,
    ApprovalCreate, Approval,
    UserCreate, UserUpdate, UserInfo,
    MyAccessSummary,
    Policy, PolicyCreate, PolicyUpdate
)
from app.services.token_validator import TokenValidator
from app.services.keycloak_client import KeycloakClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/iam-portal", tags=["IAM Portal"])
security = HTTPBearer()


class PolicyClonePayload(BaseModel):
    """Clone request for global policy bundles."""
    name: Optional[str] = None
    display_name: Optional[str] = None


def get_token_validator() -> TokenValidator:
    """Get token validator instance."""
    keycloak_client = KeycloakClient()
    return TokenValidator(keycloak_client)


def get_current_user_info(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current user info from token."""
    validator = get_token_validator()
    result = validator.validate_token(credentials.credentials)
    if not result.get("valid"):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_info = {
        "roles": result.get("roles") or [],
        "user_id": result.get("user_id") or result.get("payload", {}).get("sub"),
        "tenant_id": result.get("tenant_id") or result.get("payload", {}).get("tenant_id"),
        "realm_name": result.get("payload", {}).get("iss", "").split("/realms/")[-1] if "/realms/" in result.get("payload", {}).get("iss", "") else "sentinelgrid",
        "email": result.get("email") or result.get("payload", {}).get("email"),
        "username": result.get("username") or result.get("payload", {}).get("preferred_username")
    }
    
    logger.debug(f"🔍 [get_current_user_info] Extracted user_info: user_id={user_info['user_id']}, tenant_id={user_info['tenant_id']}, realm_name={user_info['realm_name']}, email={user_info['email']}")
    logger.debug(f"🔍 [get_current_user_info] Full token result: {result}")
    
    return user_info


def get_iam_service(
    db=Depends(get_tenant_session),
    user_info: dict = Depends(get_current_user_info)
) -> IAMPortalService:
    """
    Get IAM portal service instance.
    
    CRITICAL: tenant_id is REQUIRED for proper multi-tenant isolation.
    Requests without tenant_id will be rejected with 400.
    """
    tenant_id = user_info.get("tenant_id")
    realm_name = user_info.get("realm_name", "sentinelgrid")

    logger.debug(f"🔍 [get_iam_service] Initializing with tenant_id={tenant_id}, realm_name={realm_name}")

    # CRITICAL: Require tenant_id - no fallback logic
    if not tenant_id:
        logger.error(f"🔍 [get_iam_service] SECURITY: tenant_id missing from token for realm '{realm_name}'. Rejecting request.")
        raise HTTPException(
            status_code=400,
            detail="Tenant ID not found in token. User must be assigned to a tenant and protocol mapper must be configured correctly."
        )

    try:
        tenant_id = UUID(tenant_id)
    except (ValueError, TypeError) as e:
        logger.error(f"🔍 [get_iam_service] Invalid tenant_id format: {tenant_id}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tenant_id format: {tenant_id}"
        )

    logger.info(f"🔍 [get_iam_service] Successfully initialized with tenant_id={tenant_id}, realm_name={realm_name}")
    return IAMPortalService(db, tenant_id, realm_name)


def get_policy_admin_iam_service(
    user_info: dict = Depends(get_current_user_info),
    db=Depends(get_tenant_session),
) -> IAMPortalService:
    """Protect the legacy policy routes with the same verified role boundary."""
    get_policy_administrator(user_info)
    return get_iam_service(db, user_info)


def get_current_user_id(user_info: dict = Depends(get_current_user_info)) -> str:
    """Get current user ID from token."""
    return user_info["user_id"]


def get_catalog_access_context(context: RequestContext = Depends(get_current_request_context)):
    try:
        UUID(str(context.user_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="A verified user UUID is required")
    ensure_request_has_any_role(context, "TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN")
    return context


# ==================== Apps ====================

@router.post("/apps", response_model=App, status_code=status.HTTP_201_CREATED)
async def create_app(
    app_data: AppCreate,
    iam_service: IAMPortalService = Depends(get_iam_service),
    user_id: str = Depends(get_current_user_id)
):
    """Create a new app."""
    app = iam_service.create_app(app_data)
    if not app:
        raise HTTPException(status_code=400, detail="Failed to create app")
    return app


@router.get("/apps", response_model=List[App])
async def list_apps(
    iam_service: IAMPortalService = Depends(get_iam_service),
    user_info: dict = Depends(get_current_user_info)
):
    """List all apps for tenant."""
    return iam_service.list_apps()


@router.get("/apps/{app_id}", response_model=App)
async def get_app(
    app_id: UUID,
    iam_service: IAMPortalService = Depends(get_iam_service)
):
    """Get app by ID."""
    apps = iam_service.list_apps()
    app = next((a for a in apps if a.id == app_id), None)
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    return app


# ==================== Entitlements ====================

@router.post("/entitlements", response_model=Entitlement, status_code=status.HTTP_201_CREATED)
async def create_entitlement(
    entitlement_data: EntitlementCreate,
    mappings: List[EntitlementMappingCreate],
    iam_service: IAMPortalService = Depends(get_iam_service),
    user_id: str = Depends(get_current_user_id)
):
    """Create a new entitlement with mappings."""
    entitlement = iam_service.create_entitlement(entitlement_data, mappings)
    if not entitlement:
        raise HTTPException(status_code=400, detail="Failed to create entitlement")
    return entitlement


@router.get("/entitlements", response_model=List[Entitlement])
async def list_entitlements(
    app_id: Optional[UUID] = None,
    iam_service: IAMPortalService = Depends(get_iam_service),
    user_info: dict = Depends(get_current_user_info)
):
    """List entitlements for tenant."""
    return iam_service.list_entitlements(app_id)


# ==================== Access Profiles ====================

@router.post("/access-profiles", response_model=AccessProfile, status_code=status.HTTP_201_CREATED)
async def create_access_profile(
    profile_data: AccessProfileCreate,
    iam_service: IAMPortalService = Depends(get_iam_service),
    user_id: str = Depends(get_current_user_id)
):
    """Create a new access profile."""
    profile = iam_service.create_access_profile(profile_data)
    if not profile:
        raise HTTPException(status_code=400, detail="Failed to create access profile")
    return profile


@router.get("/access-profiles", response_model=List[AccessProfile])
async def list_access_profiles(
    iam_service: IAMPortalService = Depends(get_iam_service),
    user_info: dict = Depends(get_current_user_info)
):
    """List access profiles for tenant."""
    return iam_service.list_access_profiles()


@router.get("/access-profiles/{profile_id}", response_model=AccessProfile)
async def get_access_profile(
    profile_id: UUID,
    iam_service: IAMPortalService = Depends(get_iam_service)
):
    """Get access profile by ID."""
    profiles = iam_service.list_access_profiles()
    profile = next((p for p in profiles if p.id == profile_id), None)
    if not profile:
        raise HTTPException(status_code=404, detail="Access profile not found")
    return profile


# ==================== Birthrights ====================

@router.post("/birthrights", response_model=AccessProfile, status_code=status.HTTP_201_CREATED)
async def create_birthright(
    profile_data: AccessProfileCreate,
    iam_service: IAMPortalService = Depends(get_iam_service),
    user_id: str = Depends(get_current_user_id)
):
    """Create a new birthright access profile (baseline access)."""
    profile_data.is_birthright = True
    profile_data.is_default = False
    profile_data.is_system = False
    profile = iam_service.create_access_profile(profile_data)
    if not profile:
        raise HTTPException(status_code=400, detail="Failed to create birthright")
    return profile


@router.get("/birthrights", response_model=List[AccessProfile])
async def list_birthrights(
    iam_service: IAMPortalService = Depends(get_iam_service),
    user_info: dict = Depends(get_current_user_info)
):
    """List birthright access profiles."""
    return iam_service.list_birthrights()


# ==================== Users (People) ====================

@router.post("/users", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    iam_service: IAMPortalService = Depends(get_iam_service),
    user_id: str = Depends(get_current_user_id)
):
    """Create a new user and assign access profile."""
    # CRITICAL: tenant_id must be provided and match the current tenant context
    if not user_data.tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    if str(user_data.tenant_id) != str(iam_service.tenant_id):
        raise HTTPException(status_code=403, detail="tenant_id does not match current context")

    user = iam_service.create_user(user_data, user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Failed to create user")
    return user


@router.patch("/users/{user_id}", response_model=UserInfo)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    iam_service: IAMPortalService = Depends(get_iam_service),
    actor_id: str = Depends(get_current_user_id)
):
    """Update user attributes (name, department, team, privileged flag, enabled)."""
    try:
        updated = await iam_service.update_user(user_id, user_update, actor_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=400, detail="Failed to update user")
    return updated


@router.post("/users/{user_id}/birthrights/reapply", response_model=UserInfo)
async def reapply_birthrights(
    user_id: str,
    context: RequestContext = Depends(get_catalog_access_context),
):
    raise HTTPException(status_code=501, detail="Catalog access/lifecycle operations require schema and provider-action qualification")


@router.get("/users", response_model=List[UserInfo])
async def list_users(
    department: Optional[str] = None,
    team: Optional[str] = None,
    privileged: Optional[bool] = None,
    iam_service: IAMPortalService = Depends(get_iam_service),
    user_info: dict = Depends(get_current_user_info)
):
    """List all users for tenant."""
    logger.info(f"🔍 [list_users] Called with tenant_id={iam_service.tenant_id}, realm_name={iam_service.realm_name}")
    users = await iam_service.list_users(department_filter=department, team_filter=team, privileged_filter=privileged)
    logger.info(f"🔍 [list_users] Returning {len(users)} users")
    return users


class BulkUserActionRequest(BaseModel):
    """Bulk action payload."""
    action: str  # 'suspend' | 'offboard' | 'mark_privileged' | 'unmark_privileged'
    user_ids: List[str]


class BirthrightRuleCreate(BaseModel):
    """Create birthright rule payload."""
    name: Optional[str] = None
    attribute_key: str  # department | team
    match_value: str
    access_profile_id: UUID


class BirthrightRuleResponse(BaseModel):
    """Birthright rule response."""
    id: str
    tenant_id: str
    name: Optional[str]
    attribute_key: str
    match_value: str
    access_profile_id: str
    is_active: bool


class LifecycleSchedule(BaseModel):
    """Lifecycle schedule payload."""
    activate_at: Optional[datetime] = None
    deactivate_at: Optional[datetime] = None


class AuditEntry(BaseModel):
    action: str
    actor_user_id: Optional[str] = None
    actor_email: Optional[str] = None
    details: Optional[dict] = None
    created_at: Optional[datetime] = None


class TimelineEntry(AuditEntry):
    pass


@router.post("/users/bulk/actions")
async def bulk_user_actions(
    payload: BulkUserActionRequest,
    context: RequestContext = Depends(get_catalog_access_context),
):
    raise HTTPException(status_code=501, detail="Catalog access/lifecycle operations require schema and provider-action qualification")


@router.get("/users/{user_id}", response_model=UserInfo)
async def get_user(
    user_id: str,
    iam_service: IAMPortalService = Depends(get_iam_service)
):
    """Get user by ID."""
    user = await iam_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ==================== Birthright Rules ====================

@router.get("/birthright-rules", response_model=List[BirthrightRuleResponse])
async def list_birthright_rules(
    iam_service: IAMPortalService = Depends(get_iam_service),
):
    """List birthright rules for the tenant."""
    return iam_service.list_birthright_rules()


@router.post("/birthright-rules", response_model=BirthrightRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_birthright_rule(
    payload: BirthrightRuleCreate,
    iam_service: IAMPortalService = Depends(get_iam_service),
    actor_id: str = Depends(get_current_user_id),
):
    """Create a birthright rule (tenant-scoped)."""
    try:
        rule = iam_service.create_birthright_rule(payload.model_dump(), actor_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not rule:
        raise HTTPException(status_code=400, detail="Failed to create birthright rule")
    return rule


@router.post("/birthright-rules/preview")
async def preview_birthright_rule(
    payload: BirthrightRuleCreate,
    iam_service: IAMPortalService = Depends(get_iam_service),
):
    """Preview which users/entitlements would be affected before creating a rule."""
    try:
        return iam_service.preview_birthright_rule(payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/birthright-rules/{rule_id}")
async def delete_birthright_rule(
    rule_id: str,
    iam_service: IAMPortalService = Depends(get_iam_service),
    actor_id: str = Depends(get_current_user_id),
):
    """Delete a birthright rule (tenant-scoped)."""
    deleted = iam_service.delete_birthright_rule(rule_id, actor_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"success": True}


# ==================== Policies ====================

@router.get("/policies", response_model=List[Policy])
async def list_policies(
    policy_type: Optional[str] = None,
    iam_service: IAMPortalService = Depends(get_iam_service),
):
    """List policies for this tenant (optional type filter)."""
    return iam_service.list_policies(policy_type)


@router.get("/policies/bundles", response_model=List[Policy])
async def list_policy_bundles(
    policy_type: Optional[str] = None,
    iam_service: IAMPortalService = Depends(get_iam_service),
):
    """List global sg_admin policy bundles (clone targets)."""
    return iam_service.list_policy_bundles(policy_type)


@router.post("/policies/bundles/{bundle_id}/clone", response_model=Policy)
async def clone_policy_bundle(
    bundle_id: UUID,
    payload: PolicyClonePayload = Body(None),
    iam_service: IAMPortalService = Depends(get_policy_admin_iam_service),
    user_id: str = Depends(get_current_user_id),
):
    """Clone a global policy bundle into the current tenant."""
    pol = iam_service.clone_policy_bundle(bundle_id, payload.name if payload else None, payload.display_name if payload else None, user_id=user_id)
    if not pol:
        raise HTTPException(status_code=404, detail="Policy bundle not found or clone failed")
    return pol


@router.get("/policies/{policy_id}", response_model=Policy)
async def get_policy(
    policy_id: UUID,
    iam_service: IAMPortalService = Depends(get_iam_service),
):
    """Get a single policy."""
    pol = iam_service.get_policy(policy_id)
    if not pol:
        raise HTTPException(status_code=404, detail="Policy not found")
    return pol


@router.post("/policies", response_model=Policy, status_code=status.HTTP_201_CREATED)
async def create_policy(
    payload: PolicyCreate,
    iam_service: IAMPortalService = Depends(get_policy_admin_iam_service),
    user_id: str = Depends(get_current_user_id),
):
    pol = iam_service.create_policy(payload, created_by=user_id)
    if not pol:
        raise HTTPException(status_code=400, detail="Failed to create policy")
    return pol


@router.put("/policies/{policy_id}", response_model=Policy)
async def update_policy(
    policy_id: UUID,
    payload: PolicyUpdate,
    iam_service: IAMPortalService = Depends(get_policy_admin_iam_service),
):
    pol = iam_service.update_policy(policy_id, payload)
    if not pol:
        raise HTTPException(status_code=404, detail="Policy not found")
    return pol


@router.post("/policies/{policy_id}/approve", response_model=Policy)
async def approve_policy(
    policy_id: UUID,
    iam_service: IAMPortalService = Depends(get_policy_admin_iam_service),
    user_id: str = Depends(get_current_user_id),
):
    pol = iam_service.update_policy(policy_id, PolicyUpdate(approval_status="approved", approval_required=False))
    if not pol:
        raise HTTPException(status_code=404, detail="Policy not found")
    return pol


@router.post("/policies/{policy_id}/reject", response_model=Policy)
async def reject_policy(
    policy_id: UUID,
    iam_service: IAMPortalService = Depends(get_policy_admin_iam_service),
    user_id: str = Depends(get_current_user_id),
):
    pol = iam_service.update_policy(policy_id, PolicyUpdate(approval_status="rejected"))
    if not pol:
        raise HTTPException(status_code=404, detail="Policy not found")
    return pol


@router.get("/policies/templates/list", response_model=List[Policy])
async def list_policy_templates(
    policy_type: Optional[str] = None,
    iam_service: IAMPortalService = Depends(get_iam_service),
):
    """Placeholder: return active policies marked as templates."""
    return iam_service.list_policy_templates(policy_type)


@router.post("/policies/templates/{template_id}/create", response_model=Policy)
async def create_policy_from_template(
    template_id: UUID,
    name: str,
    display_name: str,
    iam_service: IAMPortalService = Depends(get_policy_admin_iam_service),
    user_id: str = Depends(get_current_user_id),
):
    pol = iam_service.create_policy_from_template(template_id, name, display_name, created_by=user_id)
    if not pol:
        raise HTTPException(status_code=404, detail="Template not found or creation failed")
    return pol


@router.post("/policies/evaluate")
async def evaluate_policy(
    policy_type: str,
    context: dict,
    iam_service: IAMPortalService = Depends(get_policy_admin_iam_service),
):
    """Admin simulation using the shared policy evaluator; never action authority."""
    return iam_service.evaluate_policy(policy_type, context)


# ==================== Lifecycle Scheduling ====================

@router.get("/users/{user_id}/lifecycle", response_model=LifecycleSchedule)
async def get_lifecycle_schedule(
    user_id: str,
    iam_service: IAMPortalService = Depends(get_iam_service),
):
    sched = iam_service.get_lifecycle_schedule(user_id)
    if not sched:
        return LifecycleSchedule()
    return LifecycleSchedule(**sched)


@router.post("/users/{user_id}/lifecycle", response_model=LifecycleSchedule)
async def set_lifecycle_schedule(
    user_id: str,
    payload: LifecycleSchedule,
    context: RequestContext = Depends(get_catalog_access_context),
):
    raise HTTPException(status_code=501, detail="Catalog access/lifecycle operations require schema and provider-action qualification")


@router.get("/users/{user_id}/audit", response_model=List[AuditEntry])
async def get_user_audit(
    user_id: str,
    iam_service: IAMPortalService = Depends(get_iam_service),
):
    """Get recent audit trail for a user (tenant-scoped)."""
    return iam_service.get_user_audit(user_id)


@router.get("/users/{user_id}/timeline", response_model=List[TimelineEntry])
async def get_user_timeline(
    user_id: str,
    iam_service: IAMPortalService = Depends(get_iam_service),
):
    """Get lifecycle timeline (audit + scheduled markers) for a user."""
    return iam_service.get_user_timeline(user_id)


@router.post("/users/lifecycle/run")
async def run_lifecycle_job(
    context: RequestContext = Depends(get_catalog_access_context),
):
    raise HTTPException(status_code=501, detail="Catalog access/lifecycle operations require schema and provider-action qualification")


@router.post("/users/{user_id}/entitlements", response_model=UserEntitlement)
async def grant_entitlement_to_user(
    user_id: str,
    entitlement_data: UserEntitlementCreate,
    context: RequestContext = Depends(get_catalog_access_context),
):
    raise HTTPException(status_code=501, detail="Catalog access/lifecycle operations require schema and provider-action qualification")


@router.delete("/users/{user_id}/entitlements/{entitlement_id}")
async def revoke_entitlement_from_user(
    user_id: str,
    entitlement_id: UUID,
    context: RequestContext = Depends(get_catalog_access_context),
):
    raise HTTPException(status_code=501, detail="Catalog access/lifecycle operations require schema and provider-action qualification")


@router.post("/users/{user_id}/offboard")
async def offboard_user(
    user_id: str,
    context: RequestContext = Depends(get_catalog_access_context),
):
    raise HTTPException(status_code=501, detail="Catalog access/lifecycle operations require schema and provider-action qualification")


# ==================== Access Requests (Self-Service) ====================

@router.post("/access-requests", response_model=AccessRequest, status_code=status.HTTP_201_CREATED)
async def create_access_request(
    request_data: AccessRequestCreate,
    context: RequestContext = Depends(get_catalog_access_context),
):
    raise HTTPException(status_code=501, detail="Catalog access/lifecycle operations require schema and provider-action qualification")


@router.get("/access-requests", response_model=List[AccessRequest])
async def list_access_requests(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    iam_service: IAMPortalService = Depends(get_iam_service),
    user_info: dict = Depends(get_current_user_info)
):
    """List access requests."""
    return iam_service.list_access_requests(user_id, status)


@router.get("/access-requests/{request_id}", response_model=AccessRequest)
async def get_access_request(
    request_id: UUID,
    iam_service: IAMPortalService = Depends(get_iam_service)
):
    """Get access request by ID."""
    requests = iam_service.list_access_requests()
    request = next((r for r in requests if r.id == request_id), None)
    if not request:
        raise HTTPException(status_code=404, detail="Access request not found")
    return request


@router.post("/access-requests/{request_id}/approve")
async def approve_access_request(
    request_id: UUID,
    notes: Optional[str] = None,
    context: RequestContext = Depends(get_catalog_access_context),
):
    raise HTTPException(status_code=501, detail="Catalog access/lifecycle operations require schema and provider-action qualification")


@router.post("/access-requests/{request_id}/deny")
async def deny_access_request(
    request_id: UUID,
    notes: Optional[str] = None,
    context: RequestContext = Depends(get_catalog_access_context),
):
    raise HTTPException(status_code=501, detail="Catalog access/lifecycle operations require schema and provider-action qualification")


# ==================== My Access (Self-Service Summary) ====================

@router.get("/my-access", response_model=MyAccessSummary)
async def get_my_access(
    iam_service: IAMPortalService = Depends(get_iam_service),
    user_id: str = Depends(get_current_user_id),
    user_info: dict = Depends(get_current_user_info)
):
    """Get current user's access summary."""
    # Get current entitlements
    user = await iam_service.get_user(user_id)
    current_entitlements = user.entitlements if user else []
    
    # Get pending requests
    pending_requests = iam_service.list_access_requests(user_id, status="pending")
    
    # Get available entitlements (all entitlements user doesn't have)
    all_entitlements = iam_service.list_entitlements()
    current_entitlement_ids = {e.entitlement_id for e in current_entitlements}
    available_entitlements = [e for e in all_entitlements if e.id not in current_entitlement_ids]
    
    return MyAccessSummary(
        current_entitlements=current_entitlements,
        pending_requests=pending_requests,
        available_entitlements=available_entitlements
    )
