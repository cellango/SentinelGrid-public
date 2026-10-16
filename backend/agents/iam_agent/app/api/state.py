"""Endpoint to mint OIDC state for replay protection/binding."""

from fastapi import APIRouter, HTTPException, Request
from app.api.gateway import _store_state

router = APIRouter(prefix="/auth", tags=["state"])


@router.get("/oidc/state")
async def get_oidc_state(
    request: Request,
):
    """
    Generates a state tied to tenant/idp/redirect_to for OIDC auth requests.
    """
    tenant_id = request.query_params.get("tenant_id", "")
    idp = request.query_params.get("idp", "")
    redirect_to = request.query_params.get("redirect_to", "")
    nonce = request.query_params.get("nonce", "")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id is required")
    res = _store_state({"tenant_id": tenant_id, "idp": idp, "redirect_to": redirect_to, "nonce": nonce})
    return res
