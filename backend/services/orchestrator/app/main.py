"""Orchestrator Service - Tenant + SOC Orchestration."""

import asyncio
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import create_engine
from app.core.config import settings
from app.services.metrics import metrics_tracker
from sg_core.request_tracing import RequestTracingMiddleware, configure_logging
from sg_core.service_health import (
    probe_database_engine_async,
    probe_http_dependency,
    summarize_service_health,
)
from sg_core.service_metrics import get_service_metrics

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

logger = configure_logging("orchestrator", level=settings.LOG_LEVEL)
_readiness_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
runtime_metrics = get_service_metrics(settings.SERVICE_NAME)
PROMETHEUS_MEDIA_TYPE = "text/plain; version=0.0.4; charset=utf-8"

app = FastAPI(
    title="SentinelGrid Orchestrator",
    description="Tenant and SOC orchestration service",
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
from app.api import snapshot, phishing, response, dashboard, posture, scanner_health
app.include_router(snapshot.router, prefix="/api/v1/orchestrator")
app.include_router(dashboard.router, prefix="/api/v1/orchestrator")
app.include_router(posture.router, prefix="/api/v1/orchestrator")
app.include_router(scanner_health.router, prefix="/api/v1/orchestrator")
app.include_router(phishing.router)
app.include_router(response.router)


@app.get("/")
def root():
    """Health check."""
    return {"status": "ok", "service": "orchestrator", "version": settings.VERSION}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION
    }


async def _build_readiness_payload() -> dict:
    dependencies = await asyncio.gather(
        probe_database_engine_async("database", _readiness_engine, critical=True),
        probe_http_dependency(
            "iam_agent",
            f"{settings.IAM_AGENT_URL}/health",
            verify_tls=settings.UPSTREAM_TLS_VERIFY,
            critical=True,
        ),
        probe_http_dependency(
            "siem_agent",
            f"{settings.SIEM_AGENT_URL}/health",
            verify_tls=settings.UPSTREAM_TLS_VERIFY,
            critical=False,
        ),
    )
    return summarize_service_health(settings.SERVICE_NAME, settings.VERSION, dependencies)


@app.get("/ready")
async def readiness():
    """Readiness contract for production routing and restart policy."""
    payload = await _build_readiness_payload()
    runtime_metrics.record_readiness(payload)
    return JSONResponse(status_code=200 if payload["ready"] else 503, content=payload)


@app.get("/metrics")
def metrics(format: str | None = None):
    """Expose lightweight orchestrator metrics for alerts/remediation orchestration."""
    if format == "prometheus":
        return PlainTextResponse(_prometheus_metrics_text(), media_type=PROMETHEUS_MEDIA_TYPE)
    return {
        "operations": metrics_tracker.snapshot(),
        "runtime": runtime_metrics.snapshot(),
    }


@app.get("/metrics/prometheus")
def metrics_prometheus():
    """Prometheus exposition for production scraping."""
    return PlainTextResponse(_prometheus_metrics_text(), media_type=PROMETHEUS_MEDIA_TYPE)


@app.post("/internal/orchestrator/handle_alert")
def handle_alert(request: dict):
    """Handle alert triage request."""
    # V1 stub - will call model_gateway and siem_agent
    return {
        "analysis_id": "analysis-123",
        "ai_severity": "high",
        "ai_category": "suspicious_login",
        "ai_confidence": 92.5,
        "rationale": "Based on sequence of failed logins...",
        "recommended_actions": {
            "playbook_key": "suspicious_login_basic",
            "steps_preview": ["Force password reset", "Alert user"]
        }
    }


def _prometheus_metrics_text() -> str:
    operation_snapshot = metrics_tracker.snapshot()
    lines = [runtime_metrics.prometheus_text().rstrip()]
    lines.extend(_render_operation_prometheus_lines(operation_snapshot))
    rendered = [line for line in lines if line]
    return "\n".join(rendered) + ("\n" if rendered else "")


def _render_operation_prometheus_lines(snapshot: dict) -> list[str]:
    lines = [
        "# TYPE orchestrator_operation_uptime_seconds gauge",
        f'orchestrator_operation_uptime_seconds{{service="{settings.SERVICE_NAME}"}} {snapshot.get("uptime_seconds", 0)}',
    ]

    aggregate_mappings = {
        "queued": ("orchestrator_operation_queued", "gauge"),
        "running": ("orchestrator_operation_running", "gauge"),
        "completed": ("orchestrator_operation_completed_total", "counter"),
        "failed": ("orchestrator_operation_failed_total", "counter"),
        "last_duration_ms": ("orchestrator_operation_last_duration_ms", "gauge"),
        "avg_duration_ms": ("orchestrator_operation_avg_duration_ms", "gauge"),
        "total_duration_ms": ("orchestrator_operation_total_duration_ms", "counter"),
        "samples": ("orchestrator_operation_duration_samples_total", "counter"),
    }

    for source_name, (metric_name, metric_type) in aggregate_mappings.items():
        lines.append(f"# TYPE {metric_name} {metric_type}")
        lines.append(
            f'{metric_name}{{service="{settings.SERVICE_NAME}"}} {snapshot.get(source_name, 0)}'
        )

    by_type = snapshot.get("by_type", {})
    type_mappings = {
        "queued": ("orchestrator_operation_queued_by_type", "gauge"),
        "running": ("orchestrator_operation_running_by_type", "gauge"),
        "completed": ("orchestrator_operation_completed_by_type_total", "counter"),
        "failed": ("orchestrator_operation_failed_by_type_total", "counter"),
        "last_duration_ms": ("orchestrator_operation_last_duration_ms_by_type", "gauge"),
        "avg_duration_ms": ("orchestrator_operation_avg_duration_ms_by_type", "gauge"),
        "total_duration_ms": ("orchestrator_operation_total_duration_ms_by_type", "counter"),
        "samples": ("orchestrator_operation_duration_samples_by_type_total", "counter"),
    }

    for source_name, (metric_name, metric_type) in type_mappings.items():
        lines.append(f"# TYPE {metric_name} {metric_type}")
        for operation_type, metrics in sorted(by_type.items()):
            lines.append(
                f'{metric_name}{{service="{settings.SERVICE_NAME}",operation_type="{operation_type}"}} {metrics.get(source_name, 0)}'
            )

    return lines
