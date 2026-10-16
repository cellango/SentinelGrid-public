"""
Gateway-facing auth endpoints (public) to terminate OIDC/SAML callbacks.

These endpoints are intended to sit behind the API gateway and keep Keycloak private.
For now they are stubs/placeholders to wire routing; full token/assertion handling
and domain/JIT enforcement will be added in a follow-up.
"""

from fastapi import APIRouter, HTTPException, Query, Response, Request
from fastapi.responses import RedirectResponse, JSONResponse, PlainTextResponse
import logging
import httpx
from urllib.parse import urlparse, parse_qs
from typing import Optional, List
import time
from collections import OrderedDict
import secrets
import json

from app.core.config import settings
from app.services.token_validator import TokenValidator
from app.services.keycloak_client import KeycloakClient
from app.services.keycloak_admin_client import KeycloakAdminClient
from app.api.external_idp import _ensure_https

router = APIRouter(prefix="/auth", tags=["gateway-auth"])

logger = logging.getLogger(__name__)

_state_cache = OrderedDict()  # state -> {"ts": timestamp, "meta": {...}}

async def _fetch_idp_config(alias: str) -> dict:
    """Fetch IdP instance config from Keycloak."""
    try:
        async with KeycloakAdminClient() as kc:
            resp = await kc._make_request(
                "GET", f"/realms/{settings.KEYCLOAK_REALM}/identity-provider/instances/{alias}"
            )
            if resp.status_code != 200:
                return {}
            data = resp.json()
            return data.get("config", {}) or {}
    except Exception as exc:
        logger.warning(f"Failed to fetch IdP config for {alias}: {exc}")
        return {}


async def _ensure_user_in_keycloak(email: Optional[str], tenant_id: str, default_role: Optional[str]):
    """Create user in Keycloak if missing and optionally assign default role."""
    if not email:
        return
    try:
        async with KeycloakAdminClient() as kc:
            # Check if user exists
            resp = await kc._make_request(
                "GET",
                f"/realms/{settings.KEYCLOAK_REALM}/users",
                params={"username": email},
            )
            resp.raise_for_status()
            users = resp.json() if isinstance(resp.json(), list) else []
            if users:
                user_id = users[0].get("id")
            else:
                # Create user
                user_data = {
                    "username": email,
                    "email": email,
                    "enabled": True,
                    "emailVerified": True,
                    "attributes": {"tenant_id": [tenant_id]},
                }
                create_resp = await kc._make_request(
                    "POST",
                    f"/realms/{settings.KEYCLOAK_REALM}/users",
                    json_data=user_data,
                )
                create_resp.raise_for_status()
                # Re-query to get ID
                resp2 = await kc._make_request(
                    "GET",
                    f"/realms/{settings.KEYCLOAK_REALM}/users",
                    params={"username": email},
                )
                users2 = resp2.json() if isinstance(resp2.json(), list) else []
                user_id = users2[0].get("id") if users2 else None

            if default_role and user_id:
                # Fetch role representation
                role_resp = await kc._make_request(
                    "GET",
                    f"/realms/{settings.KEYCLOAK_REALM}/roles/{default_role}",
                )
                if role_resp.status_code == 200:
                    role = role_resp.json()
                    await kc._make_request(
                        "POST",
                        f"/realms/{settings.KEYCLOAK_REALM}/users/{user_id}/role-mappings/realm",
                        json_data=[{"id": role.get("id"), "name": role.get("name")}],
                    )
    except Exception as exc:
        logger.warning(f"JIT provisioning failed for {email}: {exc}")


def _should_allow_jit(idp_config: dict) -> bool:
    """Check if JIT is enabled from IdP config; default True."""
    if not idp_config:
        return True
    val = idp_config.get("jitEnabled") or idp_config.get("jitProvisioningEnabled")
    if val is None:
        return True
    if isinstance(val, str):
        return val.lower() == "true"
    return bool(val)


def _validate_issuer(token_payload: dict):
    """Basic issuer check against configured realm."""
    expected_iss = f"{settings.KEYCLOAK_URL.rstrip('/')}/realms/{settings.KEYCLOAK_REALM}"
    iss = token_payload.get("iss")
    if iss and iss.rstrip("/") != expected_iss:
        logger.warning("Issuer mismatch: %s != %s", iss, expected_iss)
        raise HTTPException(status_code=401, detail="Invalid token issuer")


def _audit(event: str, status: str, tenant_id: str, idp: str, email: Optional[str] = None, detail: str = ""):
    """Lightweight audit/event log for IdP flows."""
    logger.info(
        "audit idp_event=%s status=%s tenant=%s idp=%s email=%s detail=%s",
        event,
        status,
        tenant_id,
        idp,
        email or "",
        detail,
    )

def _store_state(meta: dict) -> dict:
    """Generate and store state+nonce with metadata for replay protection."""
    state = secrets.token_urlsafe(24)
    nonce = meta.get("nonce") or secrets.token_urlsafe(24)
    meta["nonce"] = nonce
    now = time.time()
    ttl = settings.STATE_TTL_SECS
    # purge expired
    expired = [k for k, v in _state_cache.items() if now - v.get("ts", 0) > ttl]
    for k in expired:
        _state_cache.pop(k, None)
    if len(_state_cache) > 1000:
        _state_cache.popitem(last=False)
    _state_cache[state] = {"ts": now, "meta": meta}
    return {"state": state, "nonce": nonce}


def _store_state_with_value(state: str, meta: dict):
    """Store a provided state value (used for SAML RelayState) with TTL and replay guard."""
    if not state:
        raise HTTPException(status_code=400, detail="Missing state/relay_state")
    now = time.time()
    ttl = settings.STATE_TTL_SECS
    expired = [k for k, v in _state_cache.items() if now - v.get("ts", 0) > ttl]
    for k in expired:
        _state_cache.pop(k, None)
    if state in _state_cache:
        raise HTTPException(status_code=400, detail="State/relay_state already used")
    _state_cache[state] = {"ts": now, "meta": meta}


def _load_state_meta(expected_state: str, *, consume: bool) -> dict:
    """Load state metadata, optionally consuming the entry."""
    if not expected_state:
        raise HTTPException(status_code=400, detail="Missing state")
    entry = _state_cache.pop(expected_state, None) if consume else _state_cache.get(expected_state)
    if not entry:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    now = time.time()
    if now - entry.get("ts", 0) > settings.STATE_TTL_SECS:
        _state_cache.pop(expected_state, None)
        raise HTTPException(status_code=400, detail="State expired")
    return dict(entry.get("meta", {}) or {})


def _peek_state(expected_state: str) -> dict:
    """Load state metadata without consuming the entry."""
    return _load_state_meta(expected_state, consume=False)


def _consume_state(expected_state: str) -> dict:
    """Validate and consume state. Returns stored metadata."""
    return _load_state_meta(expected_state, consume=True)


def _resolve_state_binding(
    state_meta: dict,
    *,
    presented_tenant_id: str = "",
    presented_idp: str = "",
    presented_redirect_to: str = "",
) -> dict:
    """Resolve effective callback binding from stored state and optional compatibility query params."""
    tenant_id = str(state_meta.get("tenant_id") or "")
    idp = str(state_meta.get("idp") or "")
    redirect_to = str(state_meta.get("redirect_to") or "")

    if not tenant_id:
        raise HTTPException(status_code=400, detail="State missing tenant binding")
    if presented_tenant_id and presented_tenant_id != tenant_id:
        raise HTTPException(status_code=400, detail="State mismatch")
    if presented_idp and presented_idp != idp:
        raise HTTPException(status_code=400, detail="State mismatch")
    if presented_redirect_to and presented_redirect_to != redirect_to:
        raise HTTPException(status_code=400, detail="State mismatch")
    return {
        "tenant_id": tenant_id,
        "idp": idp,
        "redirect_to": redirect_to,
        "nonce": state_meta.get("nonce") or "",
    }

@router.get("/oidc/callback")
async def oidc_callback(
    request: Request,
    code: str = Query(..., description="Authorization code"),
    state: str = Query("", description="State/PKCE value"),
):
    """
    OIDC callback endpoint for gateway termination.

    Current implementation:
    - exchanges the code with Keycloak token endpoint (internal, using public base host)
    - validates the token locally
    - TODO: enforce allowed_domains/JIT/default_role and set SG session cookie
    """
    presented_tenant_id = request.query_params.get("tenant_id", "")
    presented_idp = request.query_params.get("idp", "")
    presented_redirect_to = request.query_params.get("redirect_to", "")
    return await _handle_oidc_callback(
        code=code,
        state=state,
        presented_tenant_id=presented_tenant_id,
        presented_idp=presented_idp,
        presented_redirect_to=presented_redirect_to,
    )


async def _handle_oidc_callback(
    *,
    code: str,
    state: str,
    presented_tenant_id: str = "",
    presented_idp: str = "",
    presented_redirect_to: str = "",
):
    logger.info(
        "Received OIDC callback code=%s state=%s tenant=%s idp=%s",
        code,
        state,
        presented_tenant_id,
        presented_idp,
    )
    state_meta = _consume_state(state)
    binding = _resolve_state_binding(
        state_meta,
        presented_tenant_id=presented_tenant_id,
        presented_idp=presented_idp,
        presented_redirect_to=presented_redirect_to,
    )
    tenant_id = binding["tenant_id"]
    idp = binding["idp"]
    redirect_to = binding["redirect_to"]
    try:
        token_url = f"{settings.KEYCLOAK_URL.rstrip('/')}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token"
        async with httpx.AsyncClient(timeout=10.0, verify=settings.KEYCLOAK_VERIFY_TLS) as client:
            resp = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": f"{settings.PUBLIC_AUTH_BASE_URL.rstrip('/')}/auth/oidc/callback?tenant_id={tenant_id}",
                    "client_id": settings.KEYCLOAK_CLIENT_ID,
                    "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            token_data = resp.json()

        access_token: Optional[str] = token_data.get("access_token")
        id_token: Optional[str] = token_data.get("id_token")
        if not access_token:
            raise HTTPException(status_code=500, detail="Missing access_token from Keycloak")

        # Validate token locally
        validator = TokenValidator(KeycloakClient())
        validation = validator.validate_token(access_token)
        if not validation.get("valid"):
            raise HTTPException(status_code=401, detail="Invalid token")
        decoded = validation.get("payload") or {}
        email = None
        try:
            _validate_issuer(decoded)
            email = validation.get("email") or decoded.get("preferred_username")
            aud = decoded.get("aud")
            if aud:
                if isinstance(aud, list):
                    if settings.KEYCLOAK_CLIENT_ID not in aud:
                        raise HTTPException(status_code=401, detail="Invalid token audience")
                elif aud != settings.KEYCLOAK_CLIENT_ID:
                    raise HTTPException(status_code=401, detail="Invalid token audience")

            token_nonce = None
            if id_token:
                id_validation = validator.validate_token(id_token)
                if not id_validation.get("valid"):
                    raise HTTPException(status_code=401, detail="Invalid id_token")
                token_nonce = (id_validation.get("payload") or {}).get("nonce")
            if not token_nonce:
                token_nonce = decoded.get("nonce")
            expected_nonce = state_meta.get("nonce")
            if expected_nonce and token_nonce != expected_nonce:
                raise HTTPException(status_code=401, detail="Invalid nonce")
        except HTTPException:
            raise
        except Exception:
            email = None

        # Enforce allowed_domains (if idp alias provided and config exists)
        idp_config = {}
        if idp:
            idp_config = await _fetch_idp_config(idp)
            allowed_config = idp_config.get("allowedDomains") or ""
            allowed_domains = [d.strip().lower() for d in allowed_config.split(",") if d.strip()]
            default_role = idp_config.get("defaultRole")
            if allowed_domains and email:
                domain = email.split("@")[-1].lower() if "@" in email else ""
                if domain and domain not in allowed_domains:
                    logger.warning("Rejecting login: domain %s not allowed for IdP %s", domain, idp)
                    raise HTTPException(status_code=403, detail="Email domain not allowed")
        else:
            default_role = None

        # Enforce JIT/basic existence
        if not _should_allow_jit(idp_config):
            raise HTTPException(status_code=403, detail="JIT provisioning disabled; user not found")
        await _ensure_user_in_keycloak(email, tenant_id, default_role)

        # Issue simple HTTP-only cookies for app consumption (dev-friendly; adjust for prod)
        target_url = redirect_to or f"{settings.PUBLIC_APP_BASE_URL.rstrip('/')}/dashboard"
        response = RedirectResponse(url=target_url, status_code=302)
        cookie_opts = {
            "httponly": True,
            "secure": True,
            "samesite": "lax",
            "path": "/",
        }
        response.set_cookie("access_token", access_token, **cookie_opts)
        refresh_token = token_data.get("refresh_token")
        if refresh_token:
            response.set_cookie("refresh_token", refresh_token, **cookie_opts)

        _audit("oidc_login", "success", tenant_id, idp or "", email)
        return response
    except httpx.HTTPStatusError as e:
        logger.error(f"Token exchange failed: {e.response.status_code} {e.response.text}")
        _audit("oidc_login", "failure", tenant_id, idp or "", None, "token_exchange_failed")
        raise HTTPException(status_code=502, detail="Keycloak token exchange failed")
    except HTTPException as he:
        _audit("oidc_login", "failure", tenant_id, idp or "", None, he.detail if hasattr(he, "detail") else "http_exception")
        raise
    except Exception as exc:
        logger.error(f"OIDC callback error: {exc}", exc_info=True)
        _audit("oidc_login", "failure", tenant_id, idp or "", None, "unexpected_error")
        raise HTTPException(status_code=500, detail="OIDC callback failed")


@router.post("/saml/acs")
async def saml_acs(
    request: Request,
):
    """
    SAML ACS endpoint: forwards assertion to Keycloak broker endpoint to avoid exposing Keycloak.

    Flow:
    - Accept SAMLResponse/RelayState from IdP
    - Forward to Keycloak broker endpoint (internal)
    - Follow redirect; return redirect to caller
    - TODO: enforce allowed_domains/JIT/default_role after token issuance (requires broker login flow)
    """
    presented_tenant_id = request.query_params.get("tenant_id", "")
    presented_idp = request.query_params.get("idp", "")
    presented_redirect_to = request.query_params.get("redirect_to", "")
    logger.info("Received SAML ACS post for tenant=%s idp=%s", presented_tenant_id, presented_idp)
    idp = presented_idp
    if not idp:
        raise HTTPException(status_code=400, detail="idp alias is required for SAML ACS")

    form_body = (await request.body()).decode()
    form = parse_qs(form_body, keep_blank_values=True)
    saml_response = form.get("SAMLResponse", [None])[0]
    relay_state = form.get("RelayState", [None])[0]
    if not saml_response:
        raise HTTPException(status_code=400, detail="Missing SAMLResponse")
    if not relay_state:
        raise HTTPException(status_code=400, detail="Missing RelayState")
    try:
        relay_state_meta = _peek_state(relay_state)
    except HTTPException as exc:
        if exc.detail not in {"Invalid or expired state", "State expired"}:
            raise
        if not presented_tenant_id:
            raise HTTPException(
                status_code=400,
                detail="tenant_id is required when RelayState is not pre-issued",
            ) from exc
        relay_state_meta = {
            "tenant_id": presented_tenant_id,
            "idp": idp,
            "redirect_to": presented_redirect_to,
            "nonce": "",
        }
        _store_state_with_value(relay_state, relay_state_meta)

    binding = _resolve_state_binding(
        relay_state_meta,
        presented_tenant_id=presented_tenant_id,
        presented_idp=presented_idp,
        presented_redirect_to=presented_redirect_to,
    )
    tenant_id = binding["tenant_id"]
    redirect_to = binding["redirect_to"]

    # Forward to Keycloak broker endpoint (internal)
    kc_endpoint = f"{settings.KEYCLOAK_URL.rstrip('/')}/realms/{settings.KEYCLOAK_REALM}/broker/{idp}/endpoint"
    try:
        async with httpx.AsyncClient(timeout=10.0, verify=settings.KEYCLOAK_VERIFY_TLS, follow_redirects=False) as client:
            resp = await client.post(
                kc_endpoint,
                data={"SAMLResponse": saml_response, "RelayState": relay_state or ""},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.is_redirect:
                location = resp.headers.get("Location")
                if location:
                    # If broker returns a code, do token exchange and enforce domains/JIT similar to OIDC
                    parsed = urlparse(location)
                    qs = parse_qs(parsed.query)
                    code = qs.get("code", [None])[0]
                    if code:
                        # Reuse OIDC callback logic for token exchange/enforcement
                        _audit("saml_acs", "success_redirect_code", tenant_id, idp or "", None)
                        return await _handle_oidc_callback(
                            code=code,
                            state=relay_state,
                            presented_tenant_id=tenant_id,
                            presented_idp=idp,
                            presented_redirect_to=redirect_to,
                        )
                    return RedirectResponse(url=location, status_code=302)
            return PlainTextResponse(content=resp.text, status_code=resp.status_code)
    except Exception as exc:
        logger.error(f"SAML ACS forward failed: {exc}", exc_info=True)
        _audit("saml_acs", "failure", tenant_id, idp or "", None, "forward_failed")
        raise HTTPException(status_code=502, detail="SAML ACS forwarding failed")
