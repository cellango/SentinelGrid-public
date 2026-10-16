"""Model Gateway Service - LLM interface."""

import asyncio
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
import logging
from starlette.requests import Request
from starlette.responses import Response
from fastapi import Header
from fastapi.responses import JSONResponse, PlainTextResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

from sg_core.service_security import parse_cors_origins, require_explicit_cors_allowlist
from sg_core.request_tracing import RequestTracingMiddleware, configure_logging
from sg_core.service_health import (
    build_dependency_status,
    probe_database_engine_async,
    summarize_service_health,
)
from sg_core.service_metrics import get_service_metrics

# Import API routers (lazy import heavy ones based on env)
from app.core.config import settings
from app.core.database import engine as db_engine
from app.api import unified_chat, adapters, embeddings, chat, openai_compat
TRAINING_ENABLED = os.getenv("DISABLE_TRAINING_ROUTES", "false").lower() not in ("1", "true", "yes")
RAG_ENABLED = os.getenv("DISABLE_RAG_ROUTES", "false").lower() not in ("1", "true", "yes")
if TRAINING_ENABLED:
    from app.api import training, git_ingestion
if RAG_ENABLED:
    from app.api import rag, knowledge_base_loader

app = FastAPI(
    title="SentinelGrid Model Gateway",
    description="Local LLM inference gateway with multi-tenant LoRA adapters",
    version="0.2.0"
)

logger = configure_logging(settings.SERVICE_NAME, level=settings.LOG_LEVEL)
runtime_metrics = get_service_metrics(settings.SERVICE_NAME)
PROMETHEUS_MEDIA_TYPE = "text/plain; version=0.0.4; charset=utf-8"

# Optional debug logging
if os.getenv("DEBUG_LOGS", "false").lower() in ("1", "true", "yes"):
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger("uvicorn.error").setLevel(logging.DEBUG)
    logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.INFO)


@app.on_event("startup")
async def preload_embeddings():
    """Warm the embedding service once at startup to avoid first-request delays."""
    import threading
    def _load():
        try:
            embeddings.get_embedding_service()
            logging.getLogger(__name__).info("Embedding service preloaded on startup")
        except Exception as exc:
            logging.getLogger(__name__).warning("Embedding service preload failed: %s", exc)
    threading.Thread(target=_load, daemon=True).start()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger = logging.getLogger("request")
    logger.debug("Request start %s %s", request.method, request.url.path)
    try:
        response: Response = await call_next(request)
        logger.debug("Request end %s %s status=%s", request.method, request.url.path, response.status_code)
        return response
    except Exception as exc:
        logger.exception("Request failed %s %s: %s", request.method, request.url.path, exc)
        raise


@app.middleware("http")
async def enforce_tenant_header(request: Request, call_next):
    """
    Require X-Tenant-ID on embedding/chat endpoints to avoid cross-tenant leakage.
    """
    path = request.url.path or ""
    if path.startswith("/api/v1/embeddings") or path.startswith("/api/v1/chat"):
        tenant_header = request.headers.get("X-Tenant-ID")
        if not tenant_header:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=400, content={"detail": "X-Tenant-ID header required"})
    return await call_next(request)

# CORS middleware
cors_origins = parse_cors_origins(os.getenv("CORS_ORIGINS"))
require_explicit_cors_allowlist(os.getenv("ENVIRONMENT", "development"), cors_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestTracingMiddleware, service_name=settings.SERVICE_NAME)

# Include routers (allow disabling heavy deps in test env)
app.include_router(unified_chat.router)
app.include_router(openai_compat.router)
app.include_router(adapters.router)
if TRAINING_ENABLED:
    app.include_router(training.router)
if RAG_ENABLED:
    app.include_router(rag.router)
    app.include_router(knowledge_base_loader.router)
if TRAINING_ENABLED:
    app.include_router(git_ingestion.router)
app.include_router(embeddings.router)
app.include_router(chat.router)


@app.get("/")
def root():
    """Health check."""
    return {
        "status": "ok",
        "service": "model-gateway",
        "version": "0.2.0",
        "features": [
            "unified_chat",
            "lora_adapters",
            "training_data",
            "adapter_training"
        ]
    }


@app.get("/health")
def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "base_model": settings.BASE_MODEL_NAME,
        "runtime": settings.LLM_RUNTIME
    }


def _probe_path_dependency(
    name: str,
    path_value: str,
    *,
    critical: bool,
    writable: bool = False,
) -> dict:
    path = Path(path_value)
    exists = path.exists()
    status = "healthy" if exists else "unhealthy"
    detail = "path_exists" if exists else "path_missing"

    if exists and writable:
        writable_ok = os.access(path, os.W_OK)
        status = "healthy" if writable_ok else "unhealthy"
        detail = "path_writable" if writable_ok else "path_not_writable"

    return build_dependency_status(
        name,
        status=status,
        critical=critical,
        detail=detail,
        extra={"path": str(path)},
    )


async def _build_readiness_payload() -> dict:
    dependencies = await asyncio.gather(
        probe_database_engine_async("database", db_engine, critical=True),
        asyncio.to_thread(
            _probe_path_dependency,
            "base_model_storage",
            settings.BASE_MODEL_PATH,
            critical=False,
        ),
        asyncio.to_thread(
            _probe_path_dependency,
            "adapter_storage",
            settings.ADAPTER_STORAGE_PATH,
            critical=False,
            writable=True,
        ),
    )
    return summarize_service_health(
        settings.SERVICE_NAME,
        settings.VERSION,
        dependencies,
        extra={
            "runtime": settings.LLM_RUNTIME,
            "training_routes_enabled": TRAINING_ENABLED,
            "rag_routes_enabled": RAG_ENABLED,
        },
    )


def _metrics_response(format: str | None = None):
    if format == "prometheus":
        return PlainTextResponse(runtime_metrics.prometheus_text(), media_type=PROMETHEUS_MEDIA_TYPE)
    return runtime_metrics.snapshot()


@app.get("/metrics")
def metrics(format: str | None = None):
    """Lightweight runtime metrics for readiness and operator troubleshooting."""
    return _metrics_response(format)


@app.get("/metrics/prometheus")
def metrics_prometheus():
    """Prometheus exposition for production scraping."""
    return _metrics_response("prometheus")


@app.get("/ready")
async def ready():
    """Readiness contract for production traffic management."""
    payload = await _build_readiness_payload()
    runtime_metrics.record_readiness(payload)
    return JSONResponse(status_code=200 if payload["ready"] else 503, content=payload)


@app.post("/internal/llm/triage-alert")
def triage_alert(request: dict):
    """
    Grounded remediation helper (deterministic fallback, tenant-scoped).
    Accepts scanner_id, target_ref, severity, summary; returns structured guidance.
    """
    try:
        scanner_id = (request or {}).get("scanner_id")
        target_ref = (request or {}).get("target_ref")
        severity = str((request or {}).get("severity") or "medium").lower()
        summary = request.get("summary") if isinstance(request, dict) else {}
    except Exception:
        scanner_id = None
        target_ref = None
        severity = "medium"
        summary = {}

    def _steps_for_scanner(scanner: str | None) -> list[str]:
        if not scanner:
            return [
                "Identify the vulnerable component or misconfiguration.",
                "Apply the vendor fix or configuration change.",
                "Re-run the scan to confirm the issue is resolved.",
            ]
        scanner_lower = scanner.lower()
        if scanner_lower in ("trivy", "zap", "semgrep", "gitleaks", "checkov", "git"):
            return [
                "Pin/upgrade the vulnerable dependency or rebuild the base image to a patched tag.",
                "Run CI security scans and smoke tests before deploy.",
                "Re-run the originating scan to confirm CVEs are cleared.",
            ]
        if scanner_lower in ("prowler", "cloud"):
            return [
                "Apply the advisory/KB or control fix for the affected cloud account.",
                "Validate control state in the cloud console.",
                "Re-run the cloud scan to verify the control passes.",
            ]
        return [
            "Validate the misconfiguration reported by the scanner.",
            "Apply the recommended secure configuration and restart affected services.",
            "Re-run the scan or functional checks to confirm resolution.",
        ]

    steps_preview = _steps_for_scanner(scanner_id)
    playbook_key = None
    if scanner_id:
        playbook_key = f"remediate_{scanner_id}"

    return {
        "ai_severity": severity,
        "ai_category": "remediation",
        "ai_confidence": 85.0,
        "rationale": f"Provide concise remediation guidance for {scanner_id or 'scanner'} on {target_ref or 'target'} (severity {severity}).",
        "recommended_actions": {
            "playbook_key": playbook_key,
            "steps_preview": steps_preview,
        },
        "model_name": "deterministic-fallback",
        "model_version": "v1",
        "usage": {
            "prompt_tokens": 0,
            "output_tokens": 0,
            "latency_ms": 10,
        },
    }
