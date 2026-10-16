"""SIEM Agent Service - SIEM integration abstraction."""

import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from app.core.config import settings
from app.core.opensearch import OpenSearchClient
from app.core.opensearch_lifecycle import ensure_ism_policy
from app.api import alerts, router
from app.core.database import engine
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sg_core.request_tracing import RequestTracingMiddleware, configure_logging
from sg_core.service_health import (
    build_dependency_status,
    probe_database_engine_async,
    probe_http_dependency,
    summarize_service_health,
)
from sg_core.service_metrics import get_service_metrics

logger = configure_logging(
    settings.SERVICE_NAME,
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
)
runtime_metrics = get_service_metrics(settings.SERVICE_NAME)
PROMETHEUS_MEDIA_TYPE = "text/plain; version=0.0.4; charset=utf-8"

app = FastAPI(
    title="SentinelGrid SIEM Agent",
    description="SIEM integration service - OpenSearch abstraction layer",
    version=settings.VERSION
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestTracingMiddleware, service_name=settings.SERVICE_NAME)

# Include routers
app.include_router(alerts.router)
app.include_router(router.router, prefix="/api/v1", tags=["router"])

# Import and include additional routers
from app.api import logs, timeline, stats, bulk, observable_types, internal, events, detection, detection_rules
app.include_router(logs.router)
app.include_router(timeline.router)
app.include_router(stats.router)
app.include_router(bulk.router)
app.include_router(observable_types.router)
app.include_router(internal.router)
app.include_router(events.router)
app.include_router(detection.router)
app.include_router(detection_rules.router)


async def wait_for_db(max_attempts: int = 30, delay_seconds: int = 2) -> None:
    """Block startup until Postgres is reachable to avoid DNS/race errors."""
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection established.")
            return
        except OperationalError as exc:
            logger.warning("Database not ready (attempt %s/%s): %s", attempt, max_attempts, exc)
            await asyncio.sleep(delay_seconds)
    raise RuntimeError("Database did not become ready in time.")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("SIEM Agent starting up...")

    # Ensure Postgres is reachable before serving traffic
    await wait_for_db()
    
    # Initialize OpenSearch client and ensure templates exist
    try:
        opensearch_client = OpenSearchClient()
        health = opensearch_client.health_check()
        if health["status"] == "healthy":
            logger.info(f"OpenSearch connection healthy: {health.get('cluster_name')}")
            # Apply Index State Management policy for retention/cost optimization
            await ensure_ism_policy(opensearch_client.client)
        else:
            logger.warning(f"OpenSearch connection issue: {health.get('error')}")
    except Exception as e:
        logger.error(f"Failed to initialize OpenSearch: {e}")
        if not settings.DEBUG_MODE:
            raise


@app.get("/")
def root():
    """Health check."""
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION
    }


@app.get("/health")
def health():
    """Detailed health check including OpenSearch connectivity."""
    try:
        opensearch_client = OpenSearchClient()
        opensearch_health = opensearch_client.health_check()
        
        return {
            "status": "healthy" if opensearch_health["status"] == "healthy" else "degraded",
            "service": settings.SERVICE_NAME,
            "opensearch": opensearch_health
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": settings.SERVICE_NAME,
            "error": str(e)
        }


async def _probe_opensearch_dependency() -> dict:
    try:
        health = await asyncio.to_thread(OpenSearchClient().health_check)
        status = "healthy" if health.get("status") == "healthy" else "unhealthy"
        detail = health.get("cluster_status") or health.get("error") or health.get("status") or "unknown"
        return build_dependency_status(
            "opensearch",
            status=status,
            critical=True,
            detail=detail,
            url=settings.OPENSEARCH_URL,
            extra={
                "cluster_name": health.get("cluster_name"),
                "nodes": health.get("number_of_nodes"),
            },
        )
    except Exception as exc:
        return build_dependency_status(
            "opensearch",
            status="unhealthy",
            critical=True,
            detail=str(exc),
            url=settings.OPENSEARCH_URL,
        )


async def _build_readiness_payload() -> dict:
    dependencies = await asyncio.gather(
        probe_database_engine_async("database", engine, critical=True),
        _probe_opensearch_dependency(),
        probe_http_dependency(
            "iam_agent",
            f"{settings.IAM_AGENT_URL}/health",
            verify_tls=settings.UPSTREAM_TLS_VERIFY,
            critical=True,
        ),
    )
    return summarize_service_health(settings.SERVICE_NAME, settings.VERSION, dependencies)


def _metrics_response(format: str | None = None):
    if format == "prometheus":
        return PlainTextResponse(runtime_metrics.prometheus_text(), media_type=PROMETHEUS_MEDIA_TYPE)
    return runtime_metrics.snapshot()


@app.get("/metrics")
def metrics(format: str | None = None):
    """Lightweight runtime metrics for SIEM readiness and dependency tracking."""
    return _metrics_response(format)


@app.get("/metrics/prometheus")
def metrics_prometheus():
    """Prometheus exposition for production scraping."""
    return _metrics_response("prometheus")


@app.get("/ready")
async def ready():
    """Readiness contract for production traffic and worker orchestration."""
    payload = await _build_readiness_payload()
    runtime_metrics.record_readiness(payload)
    return JSONResponse(status_code=200 if payload["ready"] else 503, content=payload)


# Legacy endpoint for backward compatibility
@app.get("/internal/siem/alerts/{alert_id}")
def get_alert_legacy(alert_id: str):
    """Legacy endpoint - redirects to new API structure."""
    # This endpoint can be removed once all callers are updated
    return {
        "id": alert_id,
        "external_id": "SIEM-12345",
        "source": "elastic",
        "title": "Suspicious login from new country",
        "description": "Multiple failed logins...",
        "raw_severity": "high",
        "detection_time": "2025-11-28T12:34:56Z"
    }
