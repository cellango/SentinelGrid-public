"""Bulk operations API endpoints for entitlements."""

from typing import List
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api.request_context import (
    RequestContext,
    ensure_request_tenant_matches,
    get_current_request_context,
    get_entitlement_session as get_tenant_session,
)
from app.models.entitlement import Entitlement
from app.api.entitlements import EntitlementCreate, EntitlementUpdate, _require_grant_administrator
from app.services.audit_logger import AuditLogger
from app.services.redis_cache import cache

router = APIRouter(prefix="/api/v1/entitlements", tags=["entitlements"])


class BulkCreateRequest(BaseModel):
    """Schema for bulk create request."""
    entitlements: List[EntitlementCreate]


class BulkUpdateRequest(BaseModel):
    """Schema for bulk update request."""
    updates: List[dict]  # Each dict has "id" and the fields to update


class BulkDeleteRequest(BaseModel):
    """Schema for bulk delete request."""
    entitlement_ids: List[UUID]


class BulkOperationResponse(BaseModel):
    """Schema for bulk operation response."""
    created: int = 0
    updated: int = 0
    deleted: int = 0
    failed: int = 0
    errors: List[str] = []


def _finish_bulk(db, response, field, tenant_id):
    try:
        db.commit()
    except Exception:
        db.rollback()
        response.failed += getattr(response, field)
        setattr(response, field, 0)
        response.errors.append("Grant changes and audit could not be committed")
    if getattr(response, field):
        cache.invalidate_tenant_entitlements(str(tenant_id))
    return response


@router.post("/bulk", response_model=BulkOperationResponse)
async def bulk_create_entitlements(
    request: BulkCreateRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    for item in request.entitlements:
        ensure_request_tenant_matches(request_context.tenant_id, item.tenant_id)
    actor = _require_grant_administrator(request_context)
    response = BulkOperationResponse()
    for item in request.entitlements:
        try:
            with db.begin_nested():
                existing = db.query(Entitlement).filter(
                    Entitlement.tenant_id == request_context.tenant_id,
                    Entitlement.resource_type == item.resource_type, Entitlement.resource_id == item.resource_id,
                    Entitlement.action == item.action, Entitlement.granted_to_type == item.granted_to_type,
                    Entitlement.granted_to_id == item.granted_to_id).first()
                if existing:
                    raise ValueError("Duplicate entitlement")
                payload = item.model_dump()
                payload.update(id=uuid4(), tenant_id=request_context.tenant_id, granted_by=actor)
                entitlement = Entitlement(**payload)
                db.add(entitlement)
                AuditLogger(db).log_entitlement_created(entitlement, actor, reason="Bulk grant creation")
            response.created += 1
        except Exception:
            response.failed += 1
            response.errors.append("Grant creation rejected or audit unavailable")
    return _finish_bulk(db, response, "created", request_context.tenant_id)


@router.put("/bulk", response_model=BulkOperationResponse)
async def bulk_update_entitlements(
    request: BulkUpdateRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    actor = _require_grant_administrator(request_context)
    response = BulkOperationResponse()
    for item in request.updates:
        try:
            with db.begin_nested():
                target = UUID(str(item.get("id")))
                entitlement = db.query(Entitlement).filter(Entitlement.id == target,
                    Entitlement.tenant_id == request_context.tenant_id).first()
                if entitlement is None:
                    raise ValueError("Entitlement not found")
                update = EntitlementUpdate(**{k: v for k, v in item.items() if k != "id"})
                old = {"status": entitlement.status, "expires_at": entitlement.expires_at, "metadata": entitlement.metadata_json}
                for key, value in update.model_dump(exclude_unset=True).items():
                    setattr(entitlement, key, value)
                new = {"status": entitlement.status, "expires_at": entitlement.expires_at, "metadata": entitlement.metadata_json}
                AuditLogger(db).log_entitlement_updated(entitlement, actor, old, new, reason="Bulk grant update")
            response.updated += 1
        except Exception:
            response.failed += 1
            response.errors.append("Grant update rejected or audit unavailable")
    return _finish_bulk(db, response, "updated", request_context.tenant_id)


@router.delete("/bulk", response_model=BulkOperationResponse)
async def bulk_delete_entitlements(
    request: BulkDeleteRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    db: Session = Depends(get_tenant_session)
):
    actor = _require_grant_administrator(request_context)
    response = BulkOperationResponse()
    for target in request.entitlement_ids:
        try:
            with db.begin_nested():
                entitlement = db.query(Entitlement).filter(Entitlement.id == target,
                    Entitlement.tenant_id == request_context.tenant_id).first()
                if entitlement is None:
                    raise ValueError("Entitlement not found")
                previous = entitlement.status
                entitlement.status = "revoked"
                AuditLogger(db).log_entitlement_event("revoked", entitlement.id, entitlement.tenant_id, actor,
                    changes={"status": {"old": previous, "new": "revoked"}}, reason="Bulk grant revocation")
            response.deleted += 1
        except Exception:
            response.failed += 1
            response.errors.append("Grant revocation rejected or audit unavailable")
    return _finish_bulk(db, response, "deleted", request_context.tenant_id)
