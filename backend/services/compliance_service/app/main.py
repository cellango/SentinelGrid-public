"""Compliance Service - Main FastAPI application."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.core.config import settings
from app.api import (
    agent_workflow,
    capabilities,
    coverage,
    evidence,
    framework_selections,
    frameworks,
    launch_readiness,
    remediation,
)
from app.services.observability import PROMETHEUS_MEDIA_TYPE, runtime_metrics

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="SentinelGrid Compliance Service",
    description="Compliance violation remediation - Hero Flow 5",
    version=settings.VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(remediation.router)
app.include_router(coverage.router)
app.include_router(capabilities.router)
app.include_router(frameworks.router)
app.include_router(framework_selections.router)
app.include_router(evidence.router)
app.include_router(agent_workflow.router)
app.include_router(launch_readiness.router)


@app.get("/")
def root():
    """Health check."""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "status": "healthy"
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


def _metrics_response(format: str | None = None):
    if format == "prometheus":
        return PlainTextResponse(runtime_metrics.prometheus_text(), media_type=PROMETHEUS_MEDIA_TYPE)
    return runtime_metrics.snapshot()


@app.get("/metrics")
def metrics(format: str | None = None):
    """Lightweight runtime metrics for compliance operations."""
    return _metrics_response(format)


@app.get("/metrics/prometheus")
def metrics_prometheus():
    """Prometheus exposition for production scraping."""
    return _metrics_response("prometheus")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
