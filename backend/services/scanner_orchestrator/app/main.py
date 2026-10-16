"""
Scanner Orchestrator skeleton.

Exposes a minimal API surface for enqueueing scans. Execution is asynchronous:
the request persists a scan row and dispatches work to a background worker.
In a future iteration, workers will launch per-scan containers based on
scanner_registry; currently they reuse existing handlers.
"""

import json
import os
import uuid
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, Dict, Any, List
import tempfile
import shutil
from pathlib import Path
import threading
from collections import defaultdict, deque
import time
import logging
import boto3
from botocore.client import Config as BotoConfig

import subprocess
import pathlib

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text

from sg_core.db import SessionLocal
from sg_core.jobs import handlers, parsers
from sg_core.dependencies import get_current_tenant
from sg_core.cloud.registry import CLOUD_RESOURCE_BASELINE_SCANNER_ID, resolve_scanner_alias
from .api_scans import router as scans_router
from .api_scans import _derive_fix_groups_from_findings

WORKERS = int(os.getenv("SCAN_WORKERS", "4"))
executor = ThreadPoolExecutor(max_workers=WORKERS)

# Artifact storage config (S3-only; no local fallback)
S3_ENDPOINT = os.getenv("SCAN_ARTIFACT_S3_ENDPOINT")
S3_BUCKET = os.getenv("SCAN_ARTIFACT_S3_BUCKET")
S3_ACCESS_KEY = os.getenv("SCAN_ARTIFACT_S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("SCAN_ARTIFACT_S3_SECRET_KEY")
S3_REGION = os.getenv("SCAN_ARTIFACT_S3_REGION", "us-east-1")
S3_SECURE = os.getenv("SCAN_ARTIFACT_S3_SECURE", "true").lower() in ("1", "true", "yes")

app = FastAPI(title="Scanner Orchestrator", version="0.1.4")
app.include_router(scans_router)
logger = logging.getLogger("scanner_orchestrator")


def _resolve_scanner_request(scanner_id: str, target_ref: str | None = None, payload: dict | None = None) -> tuple[str, str | None, dict]:
    resolution = resolve_scanner_alias(scanner_id)
    effective_scanner = resolution["scanner"] or scanner_id
    effective_target = target_ref or resolution.get("target")
    effective_payload = dict(payload or {})
    effective_payload["scanner_id"] = effective_scanner
    effective_payload["requested_scanner_id"] = resolution["requested_scanner"]
    if resolution.get("alias"):
        effective_payload["scanner_alias"] = resolution["metadata"]
    if effective_target:
        effective_payload["target_ref"] = effective_target
    return effective_scanner, effective_target, effective_payload

# Optional demo seed on startup
def seed_demo_scans():
    try:
        from .seed_demo_scans import seed

        seed()
        logger.info("Seeded demo scans (if not present).")
    except Exception as exc:
        logger.warning(f"Demo scan seeding skipped/failed: {exc}")

# ---------------------------------------------------------------------------
# Migrations (Flyway-style) runner on startup
# ---------------------------------------------------------------------------

def run_migrations():
    """Run SQL migrations in /app/db/migrations if present."""
    migrations_dir = pathlib.Path("/app/db/migrations")
    if not migrations_dir.exists():
        logger.info("No migrations directory found; skipping.")
        return

    logger.info("Running scanner_orchestrator migrations from %s", migrations_dir)
    db_url = os.getenv("DB_URL")
    if not db_url:
        logger.warning("DB_URL not set; skipping migrations.")
        return

    # Apply migrations using psycopg2 directly (no system psql dependency)
    try:
        import psycopg2

        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        for mig in sorted(migrations_dir.glob("V*.sql")):
            logger.info("Applying migration %s", mig.name)
            sql = mig.read_text()
            try:
                cur.execute(sql)
            except Exception as exc:
                logger.error("Migration %s failed: %s", mig.name, exc)
                cur.close()
                conn.close()
                raise
        cur.close()
        conn.close()
    except Exception as exc:
        logger.error("Migration runner failed: %s", exc)
        raise

@app.on_event("startup")
def startup_migrations():
    run_migrations()
    seed_demo_scans()

# Concurrency limits
MAX_TENANT_CONCURRENCY = int(os.getenv("SCAN_MAX_CONCURRENT_PER_TENANT", "3"))
MAX_SCANNER_CONCURRENCY = int(os.getenv("SCAN_MAX_CONCURRENT_PER_SCANNER", "5"))
RATE_LIMIT_WINDOW = int(os.getenv("SCAN_RATE_WINDOW_SECONDS", "60"))
RATE_LIMIT_MAX = int(os.getenv("SCAN_RATE_MAX_PER_WINDOW", "20"))
_slots_lock = threading.Lock()
_tenant_active: Dict[str, int] = defaultdict(int)
_scanner_active: Dict[str, int] = defaultdict(int)
_rate_lock = threading.Lock()
_tenant_rates: Dict[str, deque] = defaultdict(deque)

# Metrics (basic counters/timers)
_metrics_lock = threading.Lock()
_metrics = {
    "queued": 0,
    "running": 0,
    "completed": 0,
    "failed": 0,
    "last_duration_s": 0.0,
}


class ScanRequest(BaseModel):
    tenant_id: str = Field(..., description="Tenant ID for the scan")
    job_id: Optional[str] = Field(None, description="Origin job id (for traceability)")
    job_type: Optional[str] = Field(None, description="Origin job type")
    target: str = Field("", description="Target reference (e.g., repo path, URL, account ID)")
    scanner: Optional[str] = Field(None, description="Optional scanner override (registry name)")
    version: Optional[str] = Field(None, description="Optional scanner version/digest")
    payload: Optional[dict] = Field(default_factory=dict, description="Scanner-specific payload")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "workers": WORKERS,
        "tenant_active": dict(_tenant_active),
        "scanner_active": dict(_scanner_active),
        "rate_window": RATE_LIMIT_WINDOW,
        "rate_max": RATE_LIMIT_MAX,
        "metrics": _metrics,
    }


@app.get("/scans")
async def list_scans(current_tenant=Depends(get_current_tenant)):
    """
    Lightweight scan list; expects gateway/auth to scope by tenant.
    """
    session = SessionLocal()
    try:
        base_sql = """
            SELECT id, scanner_id, scan_type, target_ref, status, created_at, updated_at, started_at, finished_at, summary, raw_artifact_url
            FROM scans
        """
        params = {}
        tid = str(current_tenant)
        base_sql += " WHERE tenant_id = :tenant_id"
        params["tenant_id"] = tid
        base_sql += " ORDER BY created_at DESC LIMIT 50"

        rows = session.execute(text(base_sql), params).mappings().all()
        result = []
        for r in rows:
            result.append(
                {
                    "id": str(r["id"]),
                    "scanner_id": r["scanner_id"],
                    "target_ref": r["target_ref"],
                    "status": r["status"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                    "started_at": r["started_at"],
                    "finished_at": r["finished_at"],
                    "scan_type": r["scan_type"] or r["scanner_id"],
                    "summary": r["summary"],
                    "raw_artifact_url": _signed_url(S3_BUCKET, r["raw_artifact_url"].split(f"s3://{S3_BUCKET}/")[-1])
                    if r["raw_artifact_url"]
                    else None,
                }
            )
        return result
    finally:
        session.close()


PARSER_MAP = {
    "prowler": parsers.parse_prowler_json,
    "trivy": parsers.parse_trivy_json,
    "gitleaks": parsers.parse_gitleaks_json,
    "checkov": parsers.parse_checkov_json,
    "zap": parsers.parse_zap_json,
    "semgrep": parsers.parse_semgrep_json,
}


def _asset_ref(scan_type: str, payload: Dict[str, Any], target: str):
    if scan_type == "cloud":
        return "cloud_account", payload.get("cloud_connector_id") or target
    if scan_type == "git":
        return "source_repo", payload.get("repo_path") or target
    if scan_type == "app":
        return "app_url", payload.get("target_url") or target
    return scan_type, target


def _persist_findings(session, tenant_id: str, scan_type: str, scanner_id: str, scan_id: str, payload: Dict[str, Any], findings: List[Dict[str, Any]]):
    asset_type, external_id = _asset_ref(scan_type, payload, payload.get("target", ""))
    asset_id = handlers._get_or_create_asset(session, tenant_id, asset_type, external_id)  # noqa: SLF001
    handlers._insert_findings(session, tenant_id, asset_id, findings, scan_id=scan_id, scanner_id=scanner_id)  # noqa: SLF001


def _upload_artifact(tenant_id: str, scan_id: str, raw_artifact: str) -> Optional[str]:
    """
    Upload raw artifact to S3-compatible storage. Raises if not configured.
    """
    if not (S3_ENDPOINT and S3_BUCKET and S3_ACCESS_KEY and S3_SECRET_KEY):
        raise RuntimeError("artifact storage not configured")
    key = f"tenant/{tenant_id}/scans/{scan_id}.json"
    session = boto3.session.Session()
    client = session.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
        use_ssl=S3_SECURE,
        config=BotoConfig(s3={"addressing_style": "path"}),
    )
    client.put_object(Bucket=S3_BUCKET, Key=key, Body=raw_artifact.encode("utf-8"), ContentType="application/json")
    return f"s3://{S3_BUCKET}/{key}"


def _signed_url(bucket: str, key: str, expires: int = 600) -> Optional[str]:
    if not (S3_ENDPOINT and S3_BUCKET and S3_ACCESS_KEY and S3_SECRET_KEY):
        return None
    session = boto3.session.Session()
    client = session.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
        use_ssl=S3_SECURE,
        config=BotoConfig(s3={"addressing_style": "path"}),
    )
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires,
    )


def log_event(event: str, **kwargs):
    try:
        logger.info(json.dumps({"event": event, **kwargs}))
    except Exception:
        logger.info(f"{event} {kwargs}")


def _acquire_slots(tenant_id: str, scanner_id: str):
    with _slots_lock:
        if _tenant_active[tenant_id] >= MAX_TENANT_CONCURRENCY:
            raise HTTPException(status_code=429, detail="tenant concurrency limit reached")
        if _scanner_active[scanner_id] >= MAX_SCANNER_CONCURRENCY:
            raise HTTPException(status_code=429, detail="scanner concurrency limit reached")
        _tenant_active[tenant_id] += 1
        _scanner_active[scanner_id] += 1


def _release_slots(tenant_id: str, scanner_id: str):
    with _slots_lock:
        if _tenant_active[tenant_id] > 0:
            _tenant_active[tenant_id] -= 1
        if _scanner_active[scanner_id] > 0:
            _scanner_active[scanner_id] -= 1


def _check_rate_limit(tenant_id: str):
    now = time.time()
    with _rate_lock:
        dq = _tenant_rates[tenant_id]
        # prune old
        while dq and now - dq[0] > RATE_LIMIT_WINDOW:
            dq.popleft()
        if len(dq) >= RATE_LIMIT_MAX:
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        dq.append(now)


def _run_container_scan(scan_type: str, scan_id: str, req: ScanRequest, registry: Dict[str, Any]):
    """
    Execute the scanner via container using registry metadata. Returns findings and raw output.
    """
    image = registry.get("image_digest")
    if not image:
        raise RuntimeError("registry entry missing image_digest")
    limits = registry.get("default_limits") or {}
    timeout = int(limits.get("timeout_seconds", 600))
    meta = registry.get("metadata", {}) or {}
    extra_env = meta.get("env") or []
    extra_mounts = meta.get("mounts") or []
    network_mode = meta.get("network_mode")
    no_network = meta.get("no_network", False)
    read_only_fs = meta.get("read_only_rootfs", False)
    workdir = meta.get("workdir")

    args: List[str] = ["docker", "run", "--rm"]
    if limits.get("cpus"):
        args += ["--cpus", str(limits["cpus"])]
    if limits.get("memory"):
        args += ["-m", str(limits["memory"])]
    if no_network:
        args += ["--network", "none"]
    elif network_mode:
        args += ["--network", network_mode]
    if read_only_fs:
        args += ["--read-only"]
    with tempfile.TemporaryDirectory(prefix=f"scan-{scan_id}-") as tmpdir:
        tmp_path = Path(tmpdir)
        payload_path = tmp_path / "payload.json"
        output_path = tmp_path / "output.json"
        payload_path.write_text(json.dumps(req.payload or {}), encoding="utf-8")

        args += [
            "-v",
            f"{payload_path}:/work/payload.json:ro",
            "-v",
            f"{output_path}:/work/output.json",
            "-e",
            f"SCAN_TARGET={req.target}",
            "-e",
            f"SCAN_TENANT_ID={req.tenant_id}",
            "-e",
            f"SCAN_TYPE={scan_type}",
            "-e",
            "SCAN_PAYLOAD_FILE=/work/payload.json",
            "-e",
            "SCAN_OUTPUT_FILE=/work/output.json",
        ]
        if workdir:
            args += ["-w", workdir]
        # Extra env/mounts from registry metadata
        for env_kv in extra_env:
            args += ["-e", env_kv]
        for mount in extra_mounts:
            args += ["-v", mount]
        args.append(image)

        start_ts = datetime.utcnow()
        start_ts = time.time()
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        duration = time.time() - start_ts
        duration = (datetime.utcnow() - start_ts).total_seconds()
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or f"exit {proc.returncode}")

        if not output_path.exists():
            raise RuntimeError("scanner did not produce output.json")

        raw_stdout = output_path.read_text(encoding="utf-8") or "{}"
        try:
            raw_json = json.loads(raw_stdout)
        except Exception:
            raise RuntimeError("scanner output not JSON")  # noqa: B904

        parser_fn = PARSER_MAP.get(registry.get("parser"))
        if not parser_fn:
            raise RuntimeError(f"no parser for key={registry.get('parser')}")

        findings = parser_fn(raw_json)
        log_event(
            "scan.container_complete",
            scan_id=scan_id,
            scanner=registry.get("id"),
            duration_s=duration,
            findings=len(findings),
            tenant_id=req.tenant_id,
            scan_type=scan_type,
        )
        with _metrics_lock:
            _metrics["last_duration_s"] = duration
        return findings, raw_stdout


def _run_scan(scan_type: str, scan_id: str, req: ScanRequest, scanner_id: str, tenant_id: str):
    """
    Background execution. If registry has a matching entry, launch per-scan container; otherwise fallback to handlers.
    """
    session = SessionLocal()
    verification_fg_id = None
    try:
        meta = req.payload or {}
        if isinstance(meta, dict):
            summary_meta = meta.get("summary")
            if isinstance(summary_meta, str):
                try:
                    summary_meta = json.loads(summary_meta)
                except Exception:
                    summary_meta = {}
            if isinstance(summary_meta, dict) and summary_meta.get("reason") == "verification":
                verification_fg_id = summary_meta.get("fix_group_id")
    except Exception:
        verification_fg_id = None
    try:
        session.execute(
            text("UPDATE scans SET status='running', started_at=:ts, updated_at=:ts WHERE id=:id"),
            {"id": scan_id, "ts": datetime.utcnow()},
        )
        session.commit()
        with _metrics_lock:
            _metrics["running"] += 1

        job = {
            "id": req.job_id,
            "tenant_id": tenant_id,
            "job_type": req.job_type or f"{scan_type}_scan",
            "payload": req.payload or {},
        }

        registry = None
        if scanner_id != CLOUD_RESOURCE_BASELINE_SCANNER_ID:
            # Try to find registry entry
            registry = session.execute(
                text(
                    """
                    SELECT id, image_digest, parser, default_limits, metadata
                    FROM scanner_registry
                    WHERE id=:sid AND active=true
                    """
                ),
                {"sid": scanner_id},
            ).mappings().first()

        result = None
        raw_artifact = None
        raw_path = None
        try:
            if registry:
                findings, raw_artifact = _run_container_scan(scan_type, scan_id, req, registry)
                _persist_findings(session, req.tenant_id, scan_type, scanner_id, scan_id, job["payload"], findings)
                result = {"status": "ok", "container": True, "findings": len(findings)}
        except Exception as exc:  # noqa: BLE001
            result = {"warning": f"container_failed_{scanner_id}: {exc}"}

        if result is None or result.get("warning"):
            # Fallback: direct handlers
            if scanner_id == CLOUD_RESOURCE_BASELINE_SCANNER_ID:
                result = handlers.handle_cloud_resource_baseline_scan(session, job, scan_id=scan_id, scanner_id=scanner_id)
            elif scan_type == "cloud":
                result = handlers.handle_cloud_scan(session, job, scan_id=scan_id, scanner_id=scanner_id)
            elif scan_type == "git":
                result = handlers.handle_git_scan(session, job, scan_id=scan_id, scanner_id=scanner_id)
            elif scan_type == "app":
                result = handlers.handle_app_scan(session, job, scan_id=scan_id, scanner_id=scanner_id)
            else:
                raise RuntimeError(f"unsupported scan_type {scan_type}")
            log_event(
                "scan.handler_complete",
                scan_id=scan_id,
                scanner=scanner_id,
                tenant_id=req.tenant_id,
                scan_type=scan_type,
                status=result.get("status"),
            )

        s3_url = None
        if raw_artifact:
            s3_url = _upload_artifact(tenant_id, scan_id, raw_artifact)

        try:
            if scanner_id != CLOUD_RESOURCE_BASELINE_SCANNER_ID:
                _derive_fix_groups_from_findings(
                    session=session,
                    tenant_id=tenant_id,
                    scan_id=scan_id,
                    scanner_id=scanner_id,
                    target_ref=req.target,
                )
        except Exception as exc:
            logger.warning("Failed to derive FixGroups for scan %s: %s", scan_id, exc)

        session.execute(
            text(
                "UPDATE scans SET status='completed', finished_at=:ts, updated_at=:ts, summary=:summary, raw_artifact_url=:raw WHERE id=:id"
            ),
            {
                "id": scan_id,
                "ts": datetime.utcnow(),
                "summary": result or {},
                "raw": s3_url,
            },
        )
        session.commit()
        with _metrics_lock:
            _metrics["completed"] += 1
            if _metrics["running"] > 0:
                _metrics["running"] -= 1
        # Auto-close or reopen FixGroup based on verification result
        if verification_fg_id:
            try:
                session = SessionLocal()
                if result and (result.get("findings") or result.get("status") == "ok" and result.get("findings", 0) > 0):
                    # findings present → reopen
                    session.execute(
                        text(
                            """
                            UPDATE fix_groups
                            SET status = 'open', updated_at = now()
                            WHERE id = :fg_id AND tenant_id = :tenant_id
                            """
                        ),
                        {"fg_id": verification_fg_id, "tenant_id": tenant_id},
                    )
                    log_event("verification.failed", scan_id=scan_id, fix_group_id=verification_fg_id, tenant_id=tenant_id)
                else:
                    session.execute(
                        text(
                            """
                            UPDATE fix_groups
                            SET status = 'closed', updated_at = now()
                            WHERE id = :fg_id AND tenant_id = :tenant_id
                            """
                        ),
                        {"fg_id": verification_fg_id, "tenant_id": tenant_id},
                    )
                    log_event("verification.success", scan_id=scan_id, fix_group_id=verification_fg_id, tenant_id=tenant_id)
                session.commit()
            except Exception as exc:
                logger.warning("Failed to update FixGroup %s after verification: %s", verification_fg_id, exc)
            finally:
                try:
                    session.close()
                except Exception:
                    pass
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        try:
            session.execute(
                text(
                    "UPDATE scans SET status='failed', error=:err, finished_at=:ts, updated_at=:ts WHERE id=:id"
                ),
                {"id": scan_id, "err": str(exc)[:1000], "ts": datetime.utcnow()},
            )
            session.commit()
        except Exception:
            session.rollback()
        with _metrics_lock:
            _metrics["failed"] += 1
            if _metrics["running"] > 0:
                _metrics["running"] -= 1
        log_event("scan.failed", scan_id=scan_id, scanner=scanner_id, tenant_id=tenant_id, error=str(exc))
    finally:
        session.close()
        _release_slots(tenant_id, scanner_id)


@app.post("/scan/{scan_type}")
async def enqueue_scan(scan_type: str, req: ScanRequest, current_tenant=Depends(get_current_tenant)):
    """
    Persist a scan row, dispatch to background worker, and return accepted.
    """
    tenant_id = str(current_tenant)

    requested_scanner_id = req.scanner or scan_type
    scanner_id, target_ref, effective_payload = _resolve_scanner_request(
        requested_scanner_id,
        target_ref=req.target,
        payload=req.payload,
    )
    effective_req = req.model_copy(
        update={
            "scanner": scanner_id,
            "target": target_ref or "",
            "payload": effective_payload,
        }
    )
    _check_rate_limit(tenant_id)
    _acquire_slots(tenant_id, scanner_id)

    scan_id = str(uuid.uuid4())
    now = datetime.utcnow()
    session = SessionLocal()
    try:
        session.execute(
            text(
                """
                INSERT INTO scans (id, tenant_id, scanner_id, target_ref, status, created_at, updated_at, raw_artifact_url, summary)
                VALUES (:id, :tenant_id, :scanner_id, :target_ref, :status, :created_at, :updated_at, :raw_artifact_url, :summary)
                """
            ),
            {
                "id": scan_id,
                "tenant_id": tenant_id,
                "scanner_id": scanner_id,
                "target_ref": target_ref,
                "status": "queued",
                "created_at": now,
                "updated_at": now,
                "raw_artifact_url": None,
                "summary": {
                    "requested_scanner_id": requested_scanner_id,
                },
            },
        )
        session.commit()
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        session.close()
        _release_slots(tenant_id, scanner_id)
        raise HTTPException(status_code=500, detail=f"failed to persist scan: {exc}") from exc
    finally:
        session.close()

    # Dispatch async; future: fan out to worker pool that launches containers
    log_event("scan.queued", scan_id=scan_id, scan_type=scan_type, tenant_id=tenant_id, scanner=scanner_id)
    executor.submit(_run_scan, scan_type, scan_id, effective_req, scanner_id, tenant_id)

    return {
        "status": "queued",
        "scan_id": scan_id,
        "scan_type": scan_type,
        "target": target_ref,
        "scanner": scanner_id,
        "requested_scanner": requested_scanner_id,
        "version": req.version,
    }
