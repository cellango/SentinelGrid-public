"""Orchestrator proxy routes - Security snapshot and orchestration endpoints."""

import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from fastapi import Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import httpx
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

from sg_core.security import get_current_tenant
from sg_core.db import get_tenant_session
from sg_core.circuit_breaker import AsyncCircuitBreaker, CircuitBreakerOpenError
from sg_core.request_tracing import build_trace_headers
from app.core.config import settings
from app.utils.tenant_resolution import resolve_tenant_uuid

router = APIRouter()
_orchestrator_circuit_breaker = AsyncCircuitBreaker(fail_max=5, reset_timeout=30.0)


def _enforce_same_tenant(tenant_id: str, current_tenant_id: str) -> None:
    if tenant_id != current_tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Tenant ID mismatch. You can only access your own tenant's data.",
        )


def _extract_downstream_detail(response: httpx.Response):
    try:
        return response.json()
    except Exception:
        return response.text


def _build_proxy_headers(
    tenant_id: str | None = None,
    *,
    x_realm: str | None = None,
    authorization: str | None = None,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id
    if x_realm:
        headers["X-Realm"] = x_realm
    if authorization:
        headers["Authorization"] = authorization
    return build_trace_headers(headers)


async def _request_orchestrator_response(
    method: str,
    path: str,
    tenant_id: str,
    *,
    params: dict | None = None,
    payload: dict | None = None,
    timeout: float = 15.0,
) -> httpx.Response:
    url = f"{settings.ORCHESTRATOR_URL}/api/v1/orchestrator{path}"
    headers = _build_proxy_headers(tenant_id)

    async def _operation() -> httpx.Response:
        async with httpx.AsyncClient(timeout=timeout, verify=settings.UPSTREAM_TLS_VERIFY) as client:
            response = await client.request(method, url, headers=headers, params=params, json=payload)
        if response.status_code >= 500:
            raise RuntimeError(f"Orchestrator returned {response.status_code} for {path}")
        return response

    try:
        return await _orchestrator_circuit_breaker.call("api-gateway:orchestrator", _operation)
    except CircuitBreakerOpenError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Orchestrator is temporarily unavailable. Retry shortly.",
        ) from exc


async def _proxy_orchestrator_json(
    method: str,
    path: str,
    tenant_id: str,
    *,
    params: dict | None = None,
    payload: dict | None = None,
    timeout: float = 15.0,
):
    response = await _request_orchestrator_response(
        method,
        path,
        tenant_id,
        params=params,
        payload=payload,
        timeout=timeout,
    )
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=_extract_downstream_detail(response))
    return response.json()


def _serialize_sse(event: str, payload: dict | None = None) -> str:
    if payload is None:
        return f"event: {event}\n\n"
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


async def _stream_orchestrator_resource(
    request: Request,
    *,
    tenant_id: str,
    path: str,
    interval_seconds: int,
):
    async def event_stream():
        last_payload: str | None = None
        yield "retry: 5000\n\n"
        while True:
            if await request.is_disconnected():
                break
            try:
                payload = await _proxy_orchestrator_json("GET", path, tenant_id)
                serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
                if serialized != last_payload:
                    last_payload = serialized
                    yield _serialize_sse("snapshot", payload)
                else:
                    yield _serialize_sse("heartbeat", {"generated_at": payload.get("generated_at")})
            except HTTPException as exc:
                yield _serialize_sse(
                    "error",
                    {
                        "status_code": exc.status_code,
                        "detail": exc.detail,
                    },
                )
            await asyncio.sleep(interval_seconds)

    return StreamingResponse(event_stream(), media_type="text/event-stream")

# ---------------------------------------------------------------------------
# Scan enqueue proxy
# ---------------------------------------------------------------------------

@router.post("/scans")
async def enqueue_scan(
    payload: dict,
    current_tenant_id: str = Depends(get_current_tenant),
    x_realm: str | None = Header(None, alias="X-Realm"),
    tenant_slug: Optional[str] = Query(None, description="Optional tenant slug (edge convenience)"),
    db: Session = Depends(get_tenant_session),
):
    """Enqueue a scan for the current tenant."""
    tenant_uuid = resolve_tenant_uuid(current_tenant_id, db, tenant_slug, x_realm)
    headers = _build_proxy_headers(tenant_uuid, x_realm=x_realm)
    url = f"{settings.SCANNER_ORCHESTRATOR_URL}/scans"
    async with httpx.AsyncClient(timeout=15.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
        resp = await client.post(url, headers=headers, json=payload)
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)
    return resp.json()


@router.post("/scans/{scan_id}/tickets")
async def create_scan_ticket(
    scan_id: str,
    payload: dict,
    current_tenant_id: str = Depends(get_current_tenant),
    x_realm: str | None = Header(None, alias="X-Realm"),
    authorization: str | None = Header(None, alias="Authorization"),
    tenant_slug: Optional[str] = Query(None, description="Optional tenant slug (edge convenience)"),
    db: Session = Depends(get_tenant_session),
):
    """Create a ticket for a scan (e.g., from a FixGroup selection)."""
    tenant_uuid = resolve_tenant_uuid(current_tenant_id, db, tenant_slug, x_realm)
    headers = _build_proxy_headers(tenant_uuid, x_realm=x_realm, authorization=authorization)
    url = f"{settings.SCANNER_ORCHESTRATOR_URL}/scans/{scan_id}/tickets"
    async with httpx.AsyncClient(timeout=20.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
        resp = await client.post(url, headers=headers, json=payload, params={"tenant_id": tenant_uuid})
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)
    return resp.json()


@router.get("/tenant/{tenant_id}/security-snapshot")
async def get_security_snapshot(
    tenant_id: str,
    current_tenant_id: str = Depends(get_current_tenant),
):
    """
    Proxy security snapshot to orchestrator (real data).
    """
    _enforce_same_tenant(tenant_id, current_tenant_id)
    return await _proxy_orchestrator_json(
        "GET",
        f"/tenant/{tenant_id}/security-snapshot",
        tenant_id,
        timeout=30.0,
    )


# ---------------------------------------------------------------------------
# Scan status proxy (recent scans with artifacts)
# ---------------------------------------------------------------------------

@router.get("/scans/status")
async def scan_status(
    limit: int = 50,
    offset: int = 0,
    scanner: Optional[str] = Query(None, description="Comma-separated scanner_ids"),
    status: Optional[str] = Query(None, description="Comma-separated statuses"),
    q: Optional[str] = Query(None, description="Target search query"),
    current_tenant_id: str = Depends(get_current_tenant),
    x_realm: str | None = Header(None, alias="X-Realm"),
    tenant_slug: Optional[str] = Query(None, description="Optional tenant slug (edge convenience)"),
    db: Session = Depends(get_tenant_session),
):
    """Proxy scan status from scanner orchestrator, tenant-scoped."""
    tenant_uuid = resolve_tenant_uuid(current_tenant_id, db, tenant_slug, x_realm)
    headers = _build_proxy_headers(tenant_uuid, x_realm=x_realm)
    url = f"{settings.SCANNER_ORCHESTRATOR_URL}/scans/status"
    params: dict[str, object] = {"limit": limit, "offset": offset}
    if scanner:
        params["scanner"] = scanner
    if status:
        params["status"] = status
    if q:
        params["q"] = q
    async with httpx.AsyncClient(timeout=15.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
        resp = await client.get(url, headers=headers, params=params)
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)
    return resp.json()


@router.get("/scans/{scan_id}")
async def scan_detail(
    scan_id: str,
    current_tenant_id: str = Depends(get_current_tenant),
    x_realm: str | None = Header(None, alias="X-Realm"),
    tenant_slug: Optional[str] = Query(None, description="Optional tenant slug (edge convenience)"),
    db: Session = Depends(get_tenant_session),
):
    """Proxy scan detail from scanner orchestrator, tenant-scoped."""
    tenant_uuid = resolve_tenant_uuid(current_tenant_id, db, tenant_slug, x_realm)
    headers = _build_proxy_headers(tenant_uuid, x_realm=x_realm)
    url = f"{settings.SCANNER_ORCHESTRATOR_URL}/scans/{scan_id}"
    async with httpx.AsyncClient(timeout=15.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
        resp = await client.get(url, headers=headers)
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)
    return resp.json()


@router.post("/scans/{scan_id}/rescore")
async def rescore_after_scan(
    scan_id: str,
    current_tenant_id: str = Depends(get_current_tenant),
    x_realm: str | None = Header(None, alias="X-Realm"),
    tenant_slug: Optional[str] = Query(None, description="Optional tenant slug (edge convenience)"),
    db: Session = Depends(get_tenant_session),
):
    """
    Trigger posture re-score after a scan completes.
    Intended to be called by scanner orchestrator or ingest pipeline.
    """
    tenant_uuid = resolve_tenant_uuid(current_tenant_id, db, tenant_slug, x_realm)
    headers = _build_proxy_headers(tenant_uuid, x_realm=x_realm)
    url = f"{settings.ORCHESTRATOR_URL}/api/v1/orchestrator/tenant/{tenant_uuid}/posture-rescore"
    async with httpx.AsyncClient(timeout=15.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
        resp = await client.post(url, headers=headers)
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/scans/{scan_id}/fix-groups")
async def scan_fix_groups(
    scan_id: str,
    current_tenant_id: str = Depends(get_current_tenant),
    x_realm: str | None = Header(None, alias="X-Realm"),
    tenant_slug: Optional[str] = Query(None, description="Optional tenant slug (edge convenience)"),
    db: Session = Depends(get_tenant_session),
):
    """Proxy FixGroups for a scan."""
    tenant_uuid = resolve_tenant_uuid(current_tenant_id, db, tenant_slug, x_realm)
    headers = _build_proxy_headers(tenant_uuid, x_realm=x_realm)
    url = f"{settings.SCANNER_ORCHESTRATOR_URL}/scans/{scan_id}/fix-groups"
    async with httpx.AsyncClient(timeout=15.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
        resp = await client.get(url, headers=headers)
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)
    return resp.json()


@router.get("/tenant/{tenant_id}/dashboard-snapshot")
async def get_dashboard_snapshot(
    tenant_id: str,
    current_tenant_id: str = Depends(get_current_tenant)
):
    """Proxy dashboard snapshot to orchestrator (real data)."""
    _enforce_same_tenant(tenant_id, current_tenant_id)
    return await _proxy_orchestrator_json("GET", f"/tenant/{tenant_id}/dashboard-snapshot", tenant_id)

@router.get("/scanner/health")
async def scanner_health(
    current_tenant_id: str = Depends(get_current_tenant)
):
    """Proxy scanner health (registry-wide)."""
    url = f"{settings.ORCHESTRATOR_URL}/api/v1/orchestrator/scanner/health"
    async with httpx.AsyncClient(timeout=10.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
        resp = await client.get(url, headers=_build_proxy_headers())
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/scanner/registry")
async def scanner_registry(
    current_tenant_id: str = Depends(get_current_tenant)
):
    """Proxy scanner registry (enablement, last run)."""
    url = f"{settings.ORCHESTRATOR_URL}/api/v1/orchestrator/scanner/registry"
    async with httpx.AsyncClient(timeout=10.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
        resp = await client.get(url, headers=_build_proxy_headers())
    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.post("/tenant/{tenant_id}/posture-rescore")
async def posture_rescore(
    tenant_id: str,
    current_tenant_id: str = Depends(get_current_tenant)
):
    """Trigger a posture re-score (post-scan/incident)."""
    _enforce_same_tenant(tenant_id, current_tenant_id)
    return await _proxy_orchestrator_json("POST", f"/tenant/{tenant_id}/posture-rescore", tenant_id)


@router.get("/tenant/{tenant_id}/posture-score")
async def get_posture_score(
    tenant_id: str,
    current_tenant_id: str = Depends(get_current_tenant)
):
    """Proxy posture score to orchestrator."""
    _enforce_same_tenant(tenant_id, current_tenant_id)
    return await _proxy_orchestrator_json("GET", f"/tenant/{tenant_id}/posture-score", tenant_id)


@router.get("/tenant/{tenant_id}/posture-score/history")
async def get_posture_score_history(
    tenant_id: str,
    current_tenant_id: str = Depends(get_current_tenant),
    limit: int = Query(14, ge=1, le=60),
):
    """Proxy posture score history to orchestrator."""
    _enforce_same_tenant(tenant_id, current_tenant_id)
    return await _proxy_orchestrator_json(
        "GET",
        f"/tenant/{tenant_id}/posture-score/history",
        tenant_id,
        params={"limit": limit},
    )


@router.get("/tenant/{tenant_id}/dashboard-health")
async def get_dashboard_health(
    tenant_id: str,
    current_tenant_id: str = Depends(get_current_tenant)
):
    """Proxy dashboard health to orchestrator."""
    _enforce_same_tenant(tenant_id, current_tenant_id)
    return await _proxy_orchestrator_json("GET", f"/tenant/{tenant_id}/dashboard-health", tenant_id)


@router.get("/tenant/{tenant_id}/recommendations")
async def get_recommendations(
    tenant_id: str,
    current_tenant_id: str = Depends(get_current_tenant)
):
    """Proxy recommendations to orchestrator."""
    _enforce_same_tenant(tenant_id, current_tenant_id)
    return await _proxy_orchestrator_json("GET", f"/tenant/{tenant_id}/recommendations", tenant_id)


@router.get("/tenant/{tenant_id}/ai-risk-summary")
async def get_ai_risk_summary(
    tenant_id: str,
    current_tenant_id: str = Depends(get_current_tenant)
):
    """Proxy AI-risk summary to orchestrator."""
    _enforce_same_tenant(tenant_id, current_tenant_id)
    return await _proxy_orchestrator_json("GET", f"/tenant/{tenant_id}/ai-risk-summary", tenant_id)


@router.get("/tenant/{tenant_id}/now-queue")
async def get_now_queue(
    tenant_id: str,
    current_tenant_id: str = Depends(get_current_tenant)
):
    """Proxy the main dashboard Now queue to orchestrator."""
    _enforce_same_tenant(tenant_id, current_tenant_id)
    return await _proxy_orchestrator_json("GET", f"/tenant/{tenant_id}/now-queue", tenant_id)


@router.get("/tenant/{tenant_id}/operator-overview")
async def get_operator_overview(
    tenant_id: str,
    current_tenant_id: str = Depends(get_current_tenant),
):
    """Proxy composite operator overview to orchestrator."""
    _enforce_same_tenant(tenant_id, current_tenant_id)
    return await _proxy_orchestrator_json("GET", f"/tenant/{tenant_id}/operator-overview", tenant_id)


@router.get("/tenant/{tenant_id}/operator-overview/stream")
async def stream_operator_overview(
    tenant_id: str,
    request: Request,
    current_tenant_id: str = Depends(get_current_tenant),
    interval_seconds: int = Query(15, ge=5, le=60),
):
    """Stream operator overview snapshots to the frontend via SSE."""
    _enforce_same_tenant(tenant_id, current_tenant_id)
    return await _stream_orchestrator_resource(
        request,
        tenant_id=tenant_id,
        path=f"/tenant/{tenant_id}/operator-overview",
        interval_seconds=interval_seconds,
    )


@router.get("/tenant/{tenant_id}/now-queue/stream")
async def stream_now_queue(
    tenant_id: str,
    request: Request,
    current_tenant_id: str = Depends(get_current_tenant),
    interval_seconds: int = Query(15, ge=5, le=60),
):
    """Stream Now queue snapshots to the frontend via SSE."""
    _enforce_same_tenant(tenant_id, current_tenant_id)
    return await _stream_orchestrator_resource(
        request,
        tenant_id=tenant_id,
        path=f"/tenant/{tenant_id}/now-queue",
        interval_seconds=interval_seconds,
    )
