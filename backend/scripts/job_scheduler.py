"""
Minimal scheduler to enqueue recurring jobs.

This is a lightweight loop intended to be run periodically (e.g., via cron/K8s CronJob).
It reads tenant IDs from environment variables for simplicity.
"""

import os
import time
import json
import requests
import logging
from sqlalchemy import text
from sg_core.db import SessionLocal

DEFAULT_LIMIT = 3  # how many cycles before exit when run manually
DEFAULT_TENANT = os.getenv("SYSTEM_TENANT_ID", "9c7df7a9-5a0b-4412-a41c-0c0ea777b2f0")
ORCH_URL = os.getenv("SCANNER_ORCHESTRATOR_URL", "http://scanner_orchestrator:8000")
TENANT_HEALTH_URL = os.getenv("TENANT_HEALTH_URL", "http://api_gateway:8000/internal/tenant-health")

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def enqueue(db, tenant_id, job_type, payload=None):
    """Insert a job row with JSON payload."""
    db.execute(
        text(
            """
            INSERT INTO jobs (tenant_id, job_type, payload, status, attempts, max_attempts)
            VALUES (:tenant_id, :job_type, CAST(:payload AS jsonb), 'queued', 0, 5)
            """
        ),
        {
            "tenant_id": tenant_id,
            "job_type": job_type,
            "payload": json.dumps(payload or {}),
        },
    )
    db.commit()


def enqueue_orchestrator(scan_type: str, tenant_id: str, payload=None):
    """
    Attempt to enqueue directly via orchestrator; fallback to DB jobs if it fails.
    Uses the new /scans endpoint.
    """
    try:
        body = {
            "scanner_id": scan_type,
            "target_ref": payload.get("target_url") if payload else None,
            "summary": payload or {},
        }
        # Gateway is not used here; this is internal scheduler. Orchestrator enforces tenant via header.
        resp = requests.post(
            f"{ORCH_URL}/scans",
            json=body,
            headers={"X-Tenant-ID": tenant_id},
            timeout=10,
            verify=False,
        )
        resp.raise_for_status()
        logger.info(f"[scheduler] Enqueued {scan_type} scan via orchestrator for tenant={tenant_id}")
        return True
    except Exception:
        logger.warning(f"[scheduler] Failed direct enqueue for {scan_type} tenant={tenant_id}")
        return False


def tenant_is_healthy(tenant_id: str) -> bool:
    """
    Optional health check before scheduling scans.
    """
    try:
        resp = requests.get(f"{TENANT_HEALTH_URL}?tenant_id={tenant_id}", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def orchestrator_is_ready() -> bool:
    """
    Basic readiness check for the scanner orchestrator.
    """
    try:
        resp = requests.get(f"{ORCH_URL}/health", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def run_cycle():
    if not ORCH_URL:
        logger.error("[scheduler] SCANNER_ORCHESTRATOR_URL not set; skipping scheduling cycle")
        return

    db = SessionLocal()
    try:
        cloud_tenants = os.getenv("SCHEDULER_CLOUD_TENANTS", "")
        git_tenants = os.getenv("SCHEDULER_GIT_TENANTS", "")
        ai_tenants = os.getenv("SCHEDULER_AI_TENANTS", "")
        global_jobs = os.getenv("SCHEDULER_GLOBAL_JOBS", "golden_image_build")
        run_initial_scans = os.getenv("SCHEDULER_RUN_INITIAL_SCANS", "false").lower() in ("1", "true", "yes")

        if not orchestrator_is_ready():
            logger.warning("[scheduler] Orchestrator not ready; skipping this cycle")
            return

        if not any([cloud_tenants.strip(), git_tenants.strip(), ai_tenants.strip(), global_jobs.strip()]):
            logger.info("[scheduler] No tenants or jobs configured; nothing to schedule")
            return

        for tid in [t for t in cloud_tenants.split(",") if t]:
            if TENANT_HEALTH_URL and not tenant_is_healthy(tid):
                logger.warning(f"[scheduler] Tenant health check failed; skipping cloud scan for tenant={tid}")
                continue
            payload = {"include_db_security": True}
            if run_initial_scans:
                # Kick off an initial scan immediately after health check
                enqueue_orchestrator("cloud", tid, payload)
            if not enqueue_orchestrator("cloud", tid, payload):
                logger.info(f"[scheduler] Falling back to DB enqueue for cloud tenant={tid}")
                enqueue(db, tid, "cloud_daily_scan", payload)
        for tid in [t for t in git_tenants.split(",") if t]:
            if TENANT_HEALTH_URL and not tenant_is_healthy(tid):
                logger.warning(f"[scheduler] Tenant health check failed; skipping git scan for tenant={tid}")
                continue
            if run_initial_scans:
                enqueue_orchestrator("git", tid, {})
            if not enqueue_orchestrator("git", tid, {}):
                logger.info(f"[scheduler] Falling back to DB enqueue for git tenant={tid}")
                enqueue(db, tid, "git_daily_scan", {})
        for tid in [t for t in ai_tenants.split(",") if t]:
            enqueue(db, tid, "ai_daily_summary", {})
        if global_jobs:
            enqueue(db, DEFAULT_TENANT, "golden_image_build", {"image_types": ["wazuh-agent", "network-sensor", "base-os"]})
    finally:
        db.close()


if __name__ == "__main__":
    cycles = int(os.getenv("SCHEDULER_CYCLES", DEFAULT_LIMIT))
    interval = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "900"))  # default 15 minutes
    for _ in range(cycles):
        run_cycle()
        time.sleep(interval)
