"""IAM Policy API endpoints."""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.api.ai_editor import get_editor_context
from app.api.request_context import RequestContext, get_tenant_session
from app.services.policy_service import PolicyService, PolicyCloneConflict
from app.services.token_validator import TokenValidator
from app.services.keycloak_client import KeycloakClient
from app.models.policies import (
    PolicyCreate, PolicyUpdate, Policy, PolicyTemplate,
    EvaluationContext, PolicyEvaluationResult,
    PolicyAnalysis, PolicyExplanation, PolicyGenerationRequest, PolicyGenerationResult
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/iam-portal/policies", tags=["IAM Policies"])
security = HTTPBearer()


def get_token_validator() -> TokenValidator:
    """Get token validator instance."""
    # Verify signed claims without initializing a provider administrator client.
    return TokenValidator(None)


def get_current_user_info(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current user info from token."""
    validator = get_token_validator()
    result = validator.validate_token(credentials.credentials)
    if not result.get("valid"):
        raise HTTPException(status_code=401, detail="Invalid token")
    return {
        "roles": result.get("roles") or [],
        "user_id": result.get("user_id") or result.get("payload", {}).get("sub"),
        "tenant_id": result.get("tenant_id") or result.get("payload", {}).get("tenant_id"),
        "realm_name": result.get("payload", {}).get("iss", "").split("/realms/")[-1] if "/realms/" in result.get("payload", {}).get("iss", "") else "sentinelgrid",
    }


def get_policy_service(
    db=Depends(get_tenant_session),
    user_info: dict = Depends(get_current_user_info)
) -> PolicyService:
    """Get policy service instance."""
    from uuid import UUID
    tenant_id = UUID(user_info["tenant_id"]) if user_info.get("tenant_id") else None
    realm_name = user_info.get("realm_name", "sentinelgrid")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant ID not found in token")
    return PolicyService(db, tenant_id, realm_name)


def get_policy_administrator(user_info: dict = Depends(get_current_user_info)) -> dict:
    """Policy editing and simulation require verified tenant-scoped administration."""
    roles = {role.upper() for role in user_info.get("roles", [])}
    if not roles.intersection({"TENANT_ADMIN", "IAM_ADMIN", "PLATFORM_ADMIN"}):
        raise HTTPException(status_code=403, detail="Policy administrator role required")
    return user_info


def get_policy_admin_service(
    user_info: dict = Depends(get_policy_administrator),
    db=Depends(get_tenant_session),
) -> PolicyService:
    return get_policy_service(db, user_info)


def get_current_user_id(user_info: dict = Depends(get_current_user_info)) -> str:
    """Get current user ID from token."""
    return user_info["user_id"]


class ClonePolicyRequest(BaseModel):
    """Payload for cloning a seed policy."""

    name: Optional[str] = None
    display_name: Optional[str] = None

# ==================== Seed bundles (sg_admin) ====================

@router.get("/bundles", response_model=List[Policy])
async def list_seed_bundles(
    policy_service: PolicyService = Depends(get_policy_service)
):
    """List shared seed policies (from sg_admin) available to clone."""
    return policy_service.list_seed_policies()


@router.post("/bundles/{policy_id}/clone", response_model=Policy, status_code=status.HTTP_201_CREATED)
async def clone_seed_bundle(
    policy_id: UUID,
    clone_request: ClonePolicyRequest | None = None,
    policy_service: PolicyService = Depends(get_policy_admin_service),
    user_id: str = Depends(get_current_user_id)
):
    """Clone a seed policy into the current tenant."""
    try:
        cloned = policy_service.clone_seed_policy(
            policy_id,
            user_id,
            name_override=clone_request.name if clone_request else None,
            display_name_override=clone_request.display_name if clone_request else None,
        )
        if not cloned:
            raise HTTPException(status_code=404, detail="Seed policy not found or clone failed")
        return cloned
    except PolicyCloneConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))


# ==================== Policies ====================

@router.post("", response_model=Policy, status_code=status.HTTP_201_CREATED)
async def create_policy(
    policy_data: PolicyCreate,
    policy_service: PolicyService = Depends(get_policy_admin_service),
    user_id: str = Depends(get_current_user_id)
):
    """Create a new policy."""
    policy = policy_service.create_policy(policy_data, user_id)
    if not policy:
        raise HTTPException(status_code=400, detail="Failed to create policy")
    return policy


@router.get("", response_model=List[Policy])
async def list_policies(
    policy_type: Optional[str] = None,
    scope: Optional[str] = None,
    scope_id: Optional[UUID] = None,
    policy_service: PolicyService = Depends(get_policy_service),
    user_info: dict = Depends(get_current_user_info)
):
    """List policies for tenant."""
    return policy_service.list_policies(policy_type, scope, scope_id)


@router.get("/{policy_id}", response_model=Policy)
async def get_policy(
    policy_id: UUID,
    policy_service: PolicyService = Depends(get_policy_service)
):
    """Get policy by ID."""
    policy = policy_service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.put("/{policy_id}", response_model=Policy)
async def update_policy(
    policy_id: UUID,
    policy_update: PolicyUpdate,
    policy_service: PolicyService = Depends(get_policy_admin_service)
):
    """Update policy."""
    success = policy_service.update_policy(policy_id, policy_update)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update policy")
    policy = policy_service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.post("/{policy_id}/approve", response_model=Policy)
async def approve_policy(
    policy_id: UUID,
    policy_service: PolicyService = Depends(get_policy_admin_service)
):
    """Approve a policy (activate it)."""
    ok = policy_service.update_policy(policy_id, PolicyUpdate(is_active=True))
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to approve policy")
    policy = policy_service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.post("/{policy_id}/reject", response_model=Policy)
async def reject_policy(
    policy_id: UUID,
    policy_service: PolicyService = Depends(get_policy_admin_service)
):
    """Reject a policy (deactivate it)."""
    ok = policy_service.update_policy(policy_id, PolicyUpdate(is_active=False))
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to reject policy")
    policy = policy_service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.delete("/{policy_id}")
async def delete_policy(
    policy_id: UUID,
    policy_service: PolicyService = Depends(get_policy_admin_service)
):
    """Delete policy."""
    success = policy_service.delete_policy(policy_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete policy")
    return {"message": "Policy deleted"}


# ==================== Policy Templates ====================

@router.get("/templates")
async def list_templates(
    policy_type: Optional[str] = None,
    policy_service: PolicyService = Depends(get_policy_service)
):
    """List policy templates."""
    try:
        logger.info(f"📋 Getting policy templates for type: {policy_type}")
        templates = policy_service.list_templates(policy_type)
        logger.info(f"✅ Loaded {len(templates)} policy templates")
        for t in templates:
            logger.info(f"  - {t.name}: {t.display_name}")
        # Convert to dict using Pydantic V2 model_dump()
        result = []
        for t in templates:
            if hasattr(t, 'model_dump'):
                result.append(t.model_dump())
            elif hasattr(t, 'dict'):
                result.append(t.dict())
            else:
                result.append(t.__dict__)
        logger.info(f"📤 Returning {len(result)} templates")
        return result
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=503, detail="Policy templates could not be loaded") from error


@router.get("/templates/list")
async def list_templates_v2(
    policy_type: Optional[str] = None,
    policy_service: PolicyService = Depends(get_policy_service)
):
    """Alias for list_templates to avoid path conflicts with policy_id."""
    return await list_templates(policy_type, policy_service)  # type: ignore[arg-type]


@router.post("/templates/{template_id}/create", response_model=Policy, status_code=status.HTTP_201_CREATED)
async def create_policy_from_template(
    template_id: UUID,
    name: str,
    display_name: str,
    policy_service: PolicyService = Depends(get_policy_admin_service),
    user_id: str = Depends(get_current_user_id)
):
    """Create a policy from a template."""
    policy = policy_service.create_policy_from_template(template_id, name, display_name, user_id)
    if not policy:
        raise HTTPException(status_code=400, detail="Failed to create policy from template")
    return policy


# ==================== Policy Evaluation ====================

@router.post("/evaluate", response_model=PolicyEvaluationResult)
async def evaluate_policy(
    policy_type: str,
    context: EvaluationContext,
    policy_service: PolicyService = Depends(get_policy_admin_service)
):
    """Admin-only simulation; caller facts here cannot authorize an action."""
    result = policy_service.evaluate_policy(policy_type, context)
    return result


# ==================== Policy Analysis ====================

@router.get("/{policy_id}/analyze", response_model=PolicyAnalysis)
async def analyze_policy(
    policy_id: UUID,
    context: RequestContext = Depends(get_editor_context),
):
    """Unavailable legacy placeholder; use the explicit draft editor contract."""
    raise HTTPException(status_code=501, detail="Legacy policy AI placeholders are unavailable; use /api/v1/ai/editor for drafts")


@router.post("/{policy_id}/explain", response_model=PolicyExplanation)
async def explain_policy(
    policy_id: UUID,
    context: RequestContext = Depends(get_editor_context),
):
    """Unavailable legacy placeholder; use the explicit draft editor contract."""
    raise HTTPException(status_code=501, detail="Legacy policy AI placeholders are unavailable; use /api/v1/ai/editor for drafts")


@router.post("/generate", response_model=PolicyGenerationResult)
async def generate_policy(
    request: PolicyGenerationRequest,
    context: RequestContext = Depends(get_editor_context),
):
    """Unavailable legacy placeholder; use the explicit draft editor contract."""
    raise HTTPException(status_code=501, detail="Legacy policy AI placeholders are unavailable; use /api/v1/ai/editor for drafts")
