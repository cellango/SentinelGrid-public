"""
Minimal job runner loop for Postgres-backed queue.

This is a stub runner: it claims queued jobs and marks them completed with a placeholder result.
Extend dispatch() to call real handlers/executors per job_type.

Usage:
    python backend/scripts/job_runner.py  # runs until no queued jobs
"""

import os
import time
import requests
from datetime import datetime, timedelta
from sqlalchemy import text
from sg_core.db import SessionLocal
from sg_core.jobs import handlers


ORCH_URL = os.getenv("SCANNER_ORCHESTRATOR_URL", "http://scanner_orchestrator:8000")


def _call_orchestrator(scan_type: str, job):
    """
    Call the scanner orchestrator. If it fails, fall back to local handlers.
    """
    payload = {
        "tenant_id": str(job.get("tenant_id") or ""),
        "job_id": str(job.get("id") or ""),
        "job_type": job.get("job_type"),
        "target": job.get("payload", {}).get("target_url") or job.get("payload", {}).get("repo_path") or job.get("payload", {}).get("cloud_connector_id") or "",
        "payload": job.get("payload") or {},
    }
    try:
        resp = requests.post(f"{ORCH_URL}/scan/{scan_type}", json=payload, timeout=15)
        resp.raise_for_status()
        return {"status": "delegated", "orchestrator": resp.json()}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"orchestrator_failed: {exc}"}


def claim_job(session):
    row = session.execute(
        text(
            """
            SELECT id, job_type, tenant_id, payload, attempts, max_attempts
            FROM jobs
            WHERE status = 'queued' AND next_run_at <= now()
            ORDER BY created_at
            FOR UPDATE SKIP LOCKED
            LIMIT 1
            """
        )
    ).first()
    if not row:
        return None
    session.execute(
        text(
            """
            UPDATE jobs
            SET status='running', started_at=now(), attempts=attempts+1, updated_at=now()
            WHERE id=:id
            """
        ),
        {"id": row.id},
    )
    session.commit()
    return row


def complete_job(session, job_id):
    session.execute(
        text(
            """
            UPDATE jobs
            SET status='completed', finished_at=now(), updated_at=now()
            WHERE id=:id
            """
        ),
        {"id": job_id},
    )
    session.commit()


def fail_job(session, job_id, error, attempts, max_attempts):
    next_run = datetime.utcnow() + timedelta(minutes=2 * attempts)
    new_status = "failed" if attempts >= max_attempts else "queued"
    session.execute(
        text(
            """
            UPDATE jobs
            SET status=:status, error=:error, next_run_at=:next_run_at, updated_at=now()
            WHERE id=:id
            """
        ),
        {"status": new_status, "error": error[:8000], "next_run_at": next_run, "id": job_id},
    )
    session.commit()


def dispatch(session, job_row):
    """
    Dispatch by job_type to appropriate handler. Prefer orchestrator when available.
    """
    job = {
        "id": job_row.id,
        "tenant_id": job_row.tenant_id,
        "job_type": job_row.job_type,
        "payload": job_row.payload or {},
    }
    jt = job_row.job_type
    # Route to orchestrator first
    if jt in ("cloud_initial_scan", "cloud_daily_scan"):
        res = _call_orchestrator("cloud", job)
        return res if "error" not in res else handlers.handle_cloud_scan(session, job)
    if jt in ("git_initial_scan", "git_daily_scan"):
        res = _call_orchestrator("git", job)
        return res if "error" not in res else handlers.handle_git_scan(session, job)
    if jt in ("app_scan",):
        res = _call_orchestrator("app", job)
        return res if "error" not in res else handlers.handle_app_scan(session, job)
    if jt in ("ai_daily_summary",):
        # Keep handled locally until orchestrator grows AI summaries
        return handlers.handle_ai_summary(session, job)
    if jt in ("golden_image_build",):
        # Keep handled locally until orchestrator grows image builds
        return handlers.handle_golden_image(session, job)
    # Default no-op
    return {"status": "noop", "details": f"Unhandled job_type {jt}"}


def run_loop(max_idle=3):
    idle = 0
    session = SessionLocal()
    try:
        while True:
            job = claim_job(session)
            if not job:
                idle += 1
                if idle >= max_idle:
                    break
                time.sleep(1)
                continue
            idle = 0
            try:
                dispatch(session, job)
                complete_job(session, job.id)
            except Exception as exc:
                fail_job(session, job.id, str(exc), job.attempts + 1, job.max_attempts)
    finally:
        session.close()


if __name__ == "__main__":
    run_loop()
