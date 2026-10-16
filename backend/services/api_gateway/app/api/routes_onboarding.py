"""Onboarding routes for customer setup workflow (proxy to IAM Agent)."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
import httpx
import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))
from sg_core.security import get_current_tenant
from sg_core.service_metrics import get_service_metrics
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)
runtime_metrics = get_service_metrics("api-gateway")


def _forward_headers(request: Request, tenant_id: str) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "X-Tenant-ID": tenant_id,
    }
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header:
        headers["Authorization"] = auth_header
    return headers


def _record_proxy_outcome(route: str, upstream: str, outcome: str) -> None:
    runtime_metrics.increment_counter(
        "gateway_proxy_requests_total",
        route=route,
        upstream=upstream,
        outcome=outcome,
    )


def _response_outcome(status_code: int) -> str:
    return "success" if status_code < 400 else "upstream_error"


@router.get("/status")
async def get_onboarding_status(
    request: Request,
    current_tenant_id: str = Depends(get_current_tenant),
):
    """Proxy onboarding status to IAM Agent to reflect real progress/health."""
    url = f"{settings.IAM_AGENT_URL}/api/v1/onboarding/status"
    headers = _forward_headers(request, current_tenant_id)

    logger.info("🔄 Proxying onboarding status to IAM Agent")

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=headers)
            _record_proxy_outcome("onboarding_status", "iam_agent", _response_outcome(resp.status_code))
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
    except httpx.ConnectError:
        _record_proxy_outcome("onboarding_status", "iam_agent", "connect_error")
        logger.error(f"❌ IAM Agent unavailable at {settings.IAM_AGENT_URL}")
        raise HTTPException(status_code=503, detail="IAM Agent unavailable")
    except Exception as e:
        _record_proxy_outcome("onboarding_status", "iam_agent", "request_error")
        logger.error(f"❌ Onboarding proxy error: {e}")
        raise HTTPException(status_code=500, detail="Onboarding proxy error")


@router.post("/complete")
async def complete_onboarding(
    request: Request,
    current_tenant_id: str = Depends(get_current_tenant),
):
    """
    Proxy onboarding completion to IAM Agent.
    This keeps the single source of truth in the IAM service.
    """
    # First, forward to IAM Agent
    url = f"{settings.IAM_AGENT_URL}/api/v1/onboarding/complete"
    headers = _forward_headers(request, current_tenant_id)

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, headers=headers)
            _record_proxy_outcome("onboarding_complete", "iam_agent", _response_outcome(resp.status_code))
            # Best-effort: trigger initial scan for the tenant after onboarding completes
            if resp.status_code < 300:
                try:
                    # Reuse caller auth/tenant headers to enqueue scan via the orchestrator proxy
                    enqueue_headers = _forward_headers(request, current_tenant_id)
                    async with httpx.AsyncClient(timeout=10.0, verify=settings.UPSTREAM_TLS_VERIFY) as orch_client:
                        scan_resp = await orch_client.post(
                            request.url_for("enqueue_scan"),  # /api/v1/orchestrator/scans
                            headers=enqueue_headers,
                            json={"scanner_id": "baseline", "target_ref": "onboarding"},
                        )
                    _record_proxy_outcome(
                        "onboarding_complete_initial_scan_enqueue",
                        "orchestrator",
                        _response_outcome(scan_resp.status_code),
                    )
                    logger.info("✅ Enqueued initial scan after onboarding completion")
                except httpx.ConnectError as scan_exc:
                    _record_proxy_outcome(
                        "onboarding_complete_initial_scan_enqueue",
                        "orchestrator",
                        "connect_error",
                    )
                    logger.warning(f"⚠️ Failed to enqueue initial scan post-onboarding: {scan_exc}")
                except Exception as scan_exc:
                    _record_proxy_outcome(
                        "onboarding_complete_initial_scan_enqueue",
                        "orchestrator",
                        "request_error",
                    )
                    logger.warning(f"⚠️ Failed to enqueue initial scan post-onboarding: {scan_exc}")
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
    except httpx.ConnectError:
        _record_proxy_outcome("onboarding_complete", "iam_agent", "connect_error")
        logger.error(f"❌ IAM Agent unavailable at {settings.IAM_AGENT_URL}")
        raise HTTPException(status_code=503, detail="IAM Agent unavailable")
    except Exception as e:
        _record_proxy_outcome("onboarding_complete", "iam_agent", "request_error")
        logger.error(f"❌ Onboarding completion proxy error: {e}")
        raise HTTPException(status_code=500, detail="Onboarding proxy error")


# Generic proxy helper for onboarding POSTs
async def _proxy_post(request: Request, path: str, tenant_id: str):
    url = f"{settings.IAM_AGENT_URL}{path}"
    route_name = f"onboarding_{path.rsplit('/', 1)[-1].replace('-', '_')}"
    try:
        body = await request.body()
        headers = _forward_headers(request, tenant_id)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, content=body, headers=headers)
            _record_proxy_outcome(route_name, "iam_agent", _response_outcome(resp.status_code))
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
    except httpx.ConnectError:
        _record_proxy_outcome(route_name, "iam_agent", "connect_error")
        logger.error(f"❌ IAM Agent unavailable at {settings.IAM_AGENT_URL}")
        raise HTTPException(status_code=503, detail="IAM Agent unavailable")
    except Exception as e:
        _record_proxy_outcome(route_name, "iam_agent", "request_error")
        logger.error(f"❌ Onboarding proxy error for {path}: {e}")
        raise HTTPException(status_code=500, detail="Onboarding proxy error")


async def _proxy_get(request: Request, path: str, tenant_id: str):
    url = f"{settings.IAM_AGENT_URL}{path}"
    route_name = f"onboarding_{path.rsplit('/', 1)[-1].replace('-', '_')}"
    try:
        headers = _forward_headers(request, tenant_id)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            _record_proxy_outcome(route_name, "iam_agent", _response_outcome(resp.status_code))
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
    except httpx.ConnectError:
        _record_proxy_outcome(route_name, "iam_agent", "connect_error")
        logger.error(f"❌ IAM Agent unavailable at {settings.IAM_AGENT_URL}")
        raise HTTPException(status_code=503, detail="IAM Agent unavailable")
    except Exception as e:
        _record_proxy_outcome(route_name, "iam_agent", "request_error")
        logger.error(f"❌ Onboarding proxy error for {path}: {e}")
        raise HTTPException(status_code=500, detail="Onboarding proxy error")


@router.get("/cloud/providers")
async def list_cloud_provider_registry(
    request: Request,
    current_tenant_id: str = Depends(get_current_tenant),
):
    return await _proxy_get(request, "/api/v1/onboarding/cloud/providers", current_tenant_id)


@router.post("/connect-idp")
async def connect_idp(
    request: Request,
    current_tenant_id: str = Depends(get_current_tenant),
):
    return await _proxy_post(request, "/api/v1/onboarding/connect-idp", current_tenant_id)


@router.post("/connect-cloud")
async def connect_cloud(
    request: Request,
    current_tenant_id: str = Depends(get_current_tenant),
):
    return await _proxy_post(request, "/api/v1/onboarding/connect-cloud", current_tenant_id)


@router.post("/connect-aws")
async def connect_aws(
    request: Request,
    current_tenant_id: str = Depends(get_current_tenant),
):
    return await _proxy_post(request, "/api/v1/onboarding/connect-aws", current_tenant_id)


@router.post("/connect-azure")
async def connect_azure(
    request: Request,
    current_tenant_id: str = Depends(get_current_tenant),
):
    return await _proxy_post(request, "/api/v1/onboarding/connect-azure", current_tenant_id)


@router.post("/connect-gcp")
async def connect_gcp(
    request: Request,
    current_tenant_id: str = Depends(get_current_tenant),
):
    return await _proxy_post(request, "/api/v1/onboarding/connect-gcp", current_tenant_id)


@router.post("/connect-appsec")
async def connect_appsec(
    request: Request,
    current_tenant_id: str = Depends(get_current_tenant),
):
    return await _proxy_post(request, "/api/v1/onboarding/connect-appsec", current_tenant_id)


@router.post("/connect-ai")
async def connect_ai(
    request: Request,
    current_tenant_id: str = Depends(get_current_tenant),
):
    return await _proxy_post(request, "/api/v1/onboarding/connect-ai", current_tenant_id)


@router.post("/connect-ticketing")
async def connect_ticketing(
    request: Request,
    current_tenant_id: str = Depends(get_current_tenant),
):
    return await _proxy_post(request, "/api/v1/onboarding/connect-ticketing", current_tenant_id)


@router.post("/recheck-health")
async def recheck_health(
    request: Request,
    current_tenant_id: str = Depends(get_current_tenant),
):
    return await _proxy_post(request, "/api/v1/onboarding/recheck-health", current_tenant_id)


@router.post("/cloud/change-requests/{change_request_id}/approve")
async def approve_infrastructure_change_request(
    change_request_id: str,
    request: Request,
    current_tenant_id: str = Depends(get_current_tenant),
):
    return await _proxy_post(
        request,
        f"/api/v1/onboarding/cloud/change-requests/{change_request_id}/approve",
        current_tenant_id,
    )


@router.post("/cloud/change-requests/{change_request_id}/apply")
async def apply_infrastructure_change_request(
    change_request_id: str,
    request: Request,
    current_tenant_id: str = Depends(get_current_tenant),
):
    return await _proxy_post(
        request,
        f"/api/v1/onboarding/cloud/change-requests/{change_request_id}/apply",
        current_tenant_id,
    )


@router.post("/load-endpoint-sample")
async def load_endpoint_sample(
    request: Request,
    current_tenant_id: str = Depends(get_current_tenant),
):
    return await _proxy_post(request, "/api/v1/onboarding/load-endpoint-sample", current_tenant_id)
