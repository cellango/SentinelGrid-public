"""UUID ownership checks require an authenticated tenant, never a subject ID lookup."""
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException
from sg_core.tenant_session import tenant_uuid
from app.api.request_context import RequestContext, get_current_request_context


class TenantIsolationValidator:
    @staticmethod
    def validate_tenant_id(tenant_id: UUID) -> None:
        try:
            tenant_uuid(tenant_id)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="A tenant UUID is required") from exc

    @staticmethod
    def enforce_tenant_isolation(token_tenant_id: UUID, resource_tenant_id: UUID, operation: str = "access") -> None:
        try:
            matches = tenant_uuid(token_tenant_id) == tenant_uuid(resource_tenant_id)
        except (TypeError, ValueError):
            matches = False
        if not matches:
            raise HTTPException(status_code=403, detail="Access denied")

    @staticmethod
    def validate_resource_ownership(resource_tenant_id: UUID, current_user_id: UUID,
                                    resource_type: str = "resource", *, authenticated_tenant_id=None) -> None:
        # Retain legacy arguments; user_id cannot establish tenancy.
        TenantIsolationValidator.enforce_tenant_isolation(authenticated_tenant_id, resource_tenant_id)

    @staticmethod
    def get_tenant_id_for_query(tenant_id: Optional[UUID], current_user_id: UUID, *, authenticated_tenant_id=None) -> UUID:
        try:
            verified = tenant_uuid(authenticated_tenant_id)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=403, detail="Authenticated tenant required") from exc
        if tenant_id is not None:
            TenantIsolationValidator.enforce_tenant_isolation(verified, tenant_id)
        return verified

    @staticmethod
    async def get_current_user_id(context: RequestContext = Depends(get_current_request_context)) -> UUID:
        try:
            return UUID(context.user_id or "")
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Authenticated user UUID required") from exc
