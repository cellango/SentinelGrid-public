"""Kick off initial scans after tenant signup/config, with health/config validation."""

import logging
import os
import requests
from typing import List

SCAN_TYPES_ENV = os.getenv("ONBOARDING_INITIAL_SCAN_TYPES", "cloud,git")
SCAN_TYPES: List[str] = [t.strip() for t in SCAN_TYPES_ENV.split(",") if t.strip()]
ORCH_URL = os.getenv("SCANNER_ORCHESTRATOR_URL", "http://scanner_orchestrator:8000")
TENANT_HEALTH_URL = os.getenv("TENANT_HEALTH_URL", "http://api_gateway:8000/internal/tenant-health")
REQUEST_TIMEOUT = int(os.getenv("ONBOARDING_SCAN_TIMEOUT_SECONDS", "8"))

logger = logging.getLogger(__name__)


def _tenant_is_healthy(tenant_id: str) -> bool:
    if not TENANT_HEALTH_URL:
        return True
    try:
        resp = requests.get(f"{TENANT_HEALTH_URL}?tenant_id={tenant_id}", timeout=REQUEST_TIMEOUT)
        return resp.status_code == 200
    except Exception:
        return False


def _orchestrator_ready() -> bool:
    try:
        resp = requests.get(f"{ORCH_URL}/health", timeout=REQUEST_TIMEOUT)
        return resp.status_code == 200
    except Exception:
        return False


def _enqueue_scan(scan_type: str, tenant_id: str) -> None:
    body = {
        "tenant_id": tenant_id,
        "job_type": f"{scan_type}_scan",
        "payload": {},
        "target": "",
    }
    try:
        resp = requests.post(f"{ORCH_URL}/scan/{scan_type}", json=body, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        logger.info(f"[onboarding] Triggered initial {scan_type} scan for tenant={tenant_id}")
    except Exception as exc:
        logger.warning(f"[onboarding] Failed to trigger {scan_type} scan for tenant={tenant_id}: {exc}")


def trigger_initial_scans(tenant_id: str) -> None:
    """
    Trigger initial scans for a new tenant after health checks.
    Non-blocking best-effort; logs warnings on failure.
    """
    if not tenant_id:
        return
    if not ORCH_URL:
        logger.warning("[onboarding] SCANNER_ORCHESTRATOR_URL not set; skipping initial scans")
        return
    if not _orchestrator_ready():
        logger.warning("[onboarding] Orchestrator not ready; skipping initial scans")
        return
    if not _tenant_is_healthy(tenant_id):
        logger.warning(f"[onboarding] Tenant health check failed; skipping initial scans for tenant={tenant_id}")
        return

    for scan_type in SCAN_TYPES:
        _enqueue_scan(scan_type, tenant_id)
