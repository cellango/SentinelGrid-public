"""Ingestion Service - Main application."""

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from app.core.config import settings
from app.api import ingest
from app.services.batch_processor import get_batch_processor
from sg_core.request_tracing import RequestTracingMiddleware, configure_logging
from sg_core.service_health import probe_http_dependency, summarize_service_health
from sg_core.service_metrics import get_service_metrics

logger = configure_logging(settings.SERVICE_NAME, level=settings.LOG_LEVEL)
runtime_metrics = get_service_metrics(settings.SERVICE_NAME)
PROMETHEUS_MEDIA_TYPE = "text/plain; version=0.0.4; charset=utf-8"

app = FastAPI(
    title="SentinelGrid Ingestion Service",
    description="Event ingestion and normalization service",
    version=settings.VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestTracingMiddleware, service_name=settings.SERVICE_NAME)

# Include routers
app.include_router(ingest.router)


@app.get("/")
def root():
    """Health check."""
    return {"status": "ok", "service": "ingestion-service"}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    bp = get_batch_processor()
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "queue": bp.queue_summary(),
        "embeddings": bp.embedding_summary(),
    }


def _metrics_response(format: str | None = None):
    if format == "prometheus":
        return PlainTextResponse(runtime_metrics.prometheus_text(), media_type=PROMETHEUS_MEDIA_TYPE)
    return runtime_metrics.snapshot()


@app.get("/metrics")
def metrics(format: str | None = None):
    """Lightweight runtime metrics for ingestion pressure and embedding fan-out."""
    return _metrics_response(format)


@app.get("/metrics/prometheus")
def metrics_prometheus():
    """Prometheus exposition for production scraping."""
    return _metrics_response("prometheus")


async def _build_readiness_payload() -> dict:
    dependencies = [
        probe_http_dependency(
            "iam_agent",
            f"{settings.IAM_AGENT_URL}/health",
            verify_tls=settings.UPSTREAM_TLS_VERIFY,
            critical=True,
        ),
        probe_http_dependency(
            "opensearch",
            f"{settings.OPENSEARCH_URL.rstrip('/')}/_cluster/health",
            verify_tls=settings.UPSTREAM_TLS_VERIFY,
            critical=True,
        ),
    ]
    if settings.ENABLE_EMBEDDINGS:
        dependencies.append(
            probe_http_dependency(
                "model_gateway",
                f"{settings.MODEL_GATEWAY_URL.rstrip('/')}/health",
                verify_tls=settings.UPSTREAM_TLS_VERIFY,
                critical=False,
            )
        )
    payload = summarize_service_health(
        settings.SERVICE_NAME,
        settings.VERSION,
        await asyncio.gather(*dependencies),
        extra={
            "queue": get_batch_processor().queue_summary(),
            "embeddings_enabled": settings.ENABLE_EMBEDDINGS,
        },
    )
    return payload


@app.get("/ready")
async def readiness():
    """Readiness contract for production routing and restart policy."""
    payload = await _build_readiness_payload()
    runtime_metrics.record_readiness(payload)
    return JSONResponse(status_code=200 if payload["ready"] else 503, content=payload)
