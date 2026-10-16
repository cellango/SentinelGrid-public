"""Scanner health and enablement endpoints."""

import logging
import os
from fastapi import APIRouter, HTTPException
import httpx

from app.core.config import settings
from sg_core.service_metrics import get_service_metrics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scanner", tags=["scanner-health"])
runtime_metrics = get_service_metrics(settings.SERVICE_NAME)

REGISTRY_URL = os.getenv("SCANNER_ORCHESTRATOR_URL", "http://scanner_orchestrator:8000")


@router.get("/health")
async def get_scanner_health():
    """Return scanner registry health and last status per scanner."""
    try:
        async with httpx.AsyncClient(timeout=10.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
            resp = await client.get(f"{REGISTRY_URL}/health")
            resp.raise_for_status()
            payload = resp.json()
            runtime_metrics.increment_counter("scanner_health_requests_total", outcome="success")
            runtime_metrics.set_gauge("scanner_orchestrator_up", 1)
            metrics = payload.get("metrics") or {}
            runtime_metrics.set_gauge("scanner_jobs_last", float(metrics.get("queued", 0)), status="queued")
            runtime_metrics.set_gauge("scanner_jobs_last", float(metrics.get("running", 0)), status="running")
            runtime_metrics.set_gauge("scanner_jobs_last", float(metrics.get("completed", 0)), status="completed")
            runtime_metrics.set_gauge("scanner_jobs_last", float(metrics.get("failed", 0)), status="failed")
            tenant_active = payload.get("tenant_active") or {}
            scanner_active = payload.get("scanner_active") or {}
            runtime_metrics.set_gauge("scanner_tenant_active_total", float(sum(tenant_active.values())))
            runtime_metrics.set_gauge("scanner_active_total", float(sum(scanner_active.values())))
            return payload
    except httpx.HTTPStatusError as e:
        runtime_metrics.increment_counter("scanner_health_requests_total", outcome="http_error")
        runtime_metrics.set_gauge("scanner_orchestrator_up", 0)
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error(f"Failed to fetch scanner health: {e}")
        runtime_metrics.increment_counter("scanner_health_requests_total", outcome="request_error")
        runtime_metrics.set_gauge("scanner_orchestrator_up", 0)
        raise HTTPException(status_code=503, detail="Scanner health unavailable")


@router.get("/registry")
async def list_scanners():
    """List scanners with enablement/last-run metadata."""
    try:
        async with httpx.AsyncClient(timeout=10.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
            resp = await client.get(f"{REGISTRY_URL}/scanners")
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        runtime_metrics.increment_counter("scanner_registry_requests_total", outcome="http_error")
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error(f"Failed to fetch scanner registry: {e}")
        runtime_metrics.increment_counter("scanner_registry_requests_total", outcome="request_error")
        raise HTTPException(status_code=503, detail="Scanner registry unavailable")

    # Force ZAP to default disabled unless explicitly enabled
    for scanner in data.get("items", []):
        if scanner.get("id") == "zap" and scanner.get("enabled") is None:
            scanner["enabled"] = False
            scanner["notes"] = (scanner.get("notes") or "") + " (default disabled)"
    items = data.get("items", [])
    runtime_metrics.increment_counter("scanner_registry_requests_total", outcome="success")
    runtime_metrics.set_gauge(
        "scanner_registry_items_total",
        float(len(items)),
    )
    runtime_metrics.set_gauge(
        "scanner_registry_enabled_total",
        float(sum(1 for item in items if item.get("enabled") is True)),
    )
    runtime_metrics.set_gauge(
        "scanner_registry_disabled_total",
        float(sum(1 for item in items if item.get("enabled") is not True)),
    )
    return data
