"""Explicitly enabled IAM-local NHI registry; no external provider operations."""

from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.api.request_context import (
    RequestContext,
    get_current_request_context,
    get_entitlement_session,
)
from app.schemas.nhi import (
    CreateServiceAccountRequest,
    LifecycleRequest,
    AccountStatus,
    ServiceAccountResponse,
    IssuedCredentialResponse,
)
from app.services.nhi_service import NHIService, require_nhi_admin

router = APIRouter(prefix="/api/v1/nhi/service-accounts", tags=["nhi"])


def get_nhi_context(
    response: Response, context: RequestContext = Depends(get_current_request_context)
):
    require_nhi_admin(context)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return context


@router.post("", response_model=IssuedCredentialResponse, status_code=201)
def create_service_account(
    request: CreateServiceAccountRequest,
    context: RequestContext = Depends(get_nhi_context),
    db: Session = Depends(get_entitlement_session),
):
    return NHIService(db, context).create_service_account(request)


@router.get("", response_model=dict[str, list[ServiceAccountResponse] | int])
def list_service_accounts(
    status: AccountStatus | None = Query(None),
    context: RequestContext = Depends(get_nhi_context),
    db: Session = Depends(get_entitlement_session),
):
    rows = NHIService(db, context).list_service_accounts(status=status)
    return {"service_accounts": rows, "count": len(rows)}


@router.get("/expiring", response_model=dict[str, list[ServiceAccountResponse] | int])
def get_expiring_credentials(
    within_days: int = Query(14, ge=0, le=365),
    context: RequestContext = Depends(get_nhi_context),
    db: Session = Depends(get_entitlement_session),
):
    rows = NHIService(db, context).list_service_accounts(within_days=within_days)
    return {"expiring": rows, "count": len(rows), "within_days": within_days}


@router.get("/{account_id}", response_model=ServiceAccountResponse)
def get_service_account(
    account_id: UUID,
    context: RequestContext = Depends(get_nhi_context),
    db: Session = Depends(get_entitlement_session),
):
    return NHIService(db, context).get_service_account(account_id)


@router.post("/{account_id}/rotate", response_model=IssuedCredentialResponse)
def rotate_credentials(
    account_id: UUID,
    request: LifecycleRequest,
    context: RequestContext = Depends(get_nhi_context),
    db: Session = Depends(get_entitlement_session),
):
    return NHIService(db, context).transition(account_id, "rotate", request)


@router.post("/{account_id}/deactivate", response_model=ServiceAccountResponse)
def deactivate_service_account(
    account_id: UUID,
    request: LifecycleRequest,
    context: RequestContext = Depends(get_nhi_context),
    db: Session = Depends(get_entitlement_session),
):
    return NHIService(db, context).transition(account_id, "deactivate", request)


@router.post("/{account_id}/activate", response_model=IssuedCredentialResponse)
def activate_service_account(
    account_id: UUID,
    request: LifecycleRequest,
    context: RequestContext = Depends(get_nhi_context),
    db: Session = Depends(get_entitlement_session),
):
    return NHIService(db, context).transition(account_id, "activate", request)


@router.delete("/{account_id}", response_model=ServiceAccountResponse)
def delete_service_account(
    account_id: UUID,
    request: LifecycleRequest,
    context: RequestContext = Depends(get_nhi_context),
    db: Session = Depends(get_entitlement_session),
):
    return NHIService(db, context).transition(account_id, "delete", request)
