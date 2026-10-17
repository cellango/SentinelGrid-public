"""API Gateway - Public REST API for frontend."""

import asyncio
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
import sys
import os

# Add libs directory to path for imports
libs_path = os.path.join(os.path.dirname(__file__), "../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)
else:
    # Fallback: libs should be in /app/libs in container
    sys.path.insert(0, "/app/libs")

from app.api import (
    routes_alerts, routes_incidents, routes_playbooks, routes_chat,
    routes_integrations, routes_orchestrator, routes_reports, routes_iam,
    routes_posture, routes_onboarding, routes_siem, routes_agents, routes_hardened_images,
    routes_compliance, routes_iam_portal, routes_devices, routes_auth, routes_soar, routes_audit,
    routes_jobs, routes_playbook_executions, routes_ticketing, routes_governance,
    routes_ai_shield,
    routes_ingest,
)
from app.core.config import settings
from app.core.request_identity import require_gateway_identity
from sg_core.request_credentials import AuthCookieMiddleware
from sg_core.security import get_current_tenant
from sg_core.request_tracing import RequestTracingMiddleware, configure_logging
from sg_core.service_health import probe_http_dependency, summarize_service_health
from sg_core.service_metrics import get_service_metrics

# Tool registry seeding is optional; when the monorepo isn't bundled in the image, skip gracefully.
logger = configure_logging("api-gateway")
runtime_metrics = get_service_metrics("api-gateway")

try:
    from backend.scripts.seed_tool_registry import run_seed  # type: ignore
except Exception:  # pragma: no cover - best-effort import for dev images
    def run_seed(*args, **kwargs):
        logger.info("backend.scripts.seed_tool_registry not available; skipping seed_tool_registry")
        return 0

app = FastAPI(
    dependencies=[Depends(require_gateway_identity)],
    title="SentinelGrid API",
    description="AI-driven Security-as-a-Service API",
    version="0.1.0"
)
# Bind the verifier and user registration policy to this application's owned config.
app.state.iam_verification_settings = settings.verification_settings()
app.state.user_principal_settings = settings.user_principal_settings()
# Avoid HTTP 307 redirects that leak http:// locations when clients omit trailing slashes
app.router.redirect_slashes = False
PROMETHEUS_MEDIA_TYPE = "text/plain; version=0.0.4; charset=utf-8"

# CORS wraps credential rejection as well as successful route responses.
app.add_middleware(AuthCookieMiddleware)
# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestTracingMiddleware, service_name="api-gateway")

# Include routers
app.include_router(routes_alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(routes_incidents.router, prefix="/api/v1/incidents", tags=["incidents"])
app.include_router(routes_playbook_executions.router, prefix="/api/v1/playbook-executions", tags=["playbook-executions"])
app.include_router(routes_playbooks.router, prefix="/api/v1/playbooks", tags=["playbooks"])
app.include_router(routes_playbooks.clone_router, prefix="/api/v1", tags=["playbooks"])
# Legacy paths (without /v1) to avoid breaking dashboards
app.include_router(routes_playbooks.router, prefix="/api/playbooks", tags=["playbooks-legacy"])
app.include_router(routes_playbooks.clone_router, prefix="/api", tags=["playbooks-legacy"])
app.include_router(routes_chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(routes_integrations.router, prefix="/api/v1/integrations", tags=["integrations"])
app.include_router(routes_orchestrator.router, prefix="/api/v1/orchestrator", tags=["orchestrator"])
# Backward-compat: older frontend chunks may call /api/orchestrator/*
app.include_router(routes_orchestrator.router, prefix="/api/orchestrator", tags=["orchestrator-legacy"])
app.include_router(routes_reports.router, prefix="/api/v1/reports", tags=["reports"])
# Legacy path for frontend calling /api/reports
app.include_router(routes_reports.router, prefix="/api/reports", tags=["reports-legacy"])
app.include_router(routes_iam.router, prefix="/api/v1/iam", tags=["iam"])
app.include_router(routes_posture.router, prefix="/api/v1/posture", tags=["posture"])
# Legacy prefixes for UI calls still hitting /api/iam and /api/posture
app.include_router(routes_iam.router, prefix="/api/iam", tags=["iam-legacy"])
app.include_router(routes_posture.router, prefix="/api/posture", tags=["posture-legacy"])
app.include_router(routes_onboarding.router, prefix="/api/v1/onboarding", tags=["onboarding"])
app.include_router(routes_siem.router, prefix="/api/v1/siem", tags=["siem"])
# Legacy SIEM paths without /v1 for dashboards/widgets expecting /api/siem/*
app.include_router(routes_siem.router, prefix="/api/siem", tags=["siem-legacy"])
app.include_router(routes_agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(routes_hardened_images.router, prefix="/api/v1/hardened-images", tags=["hardened-images"])
app.include_router(routes_compliance.router, prefix="/api/v1/compliance", tags=["compliance"])
app.include_router(routes_governance.router, prefix="/api/v1/governance", tags=["governance"])
app.include_router(routes_governance.router, prefix="/api/governance", tags=["governance-legacy"])
app.include_router(routes_iam_portal.router, prefix="/api/iam-portal", tags=["iam-portal"])
app.include_router(routes_devices.router, prefix="/api/v1/devices", tags=["devices"])
app.include_router(routes_auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(routes_soar.router, prefix="/api/v1/soar", tags=["soar"])
app.include_router(routes_audit.router, prefix="/api/v1", tags=["audit"])
app.include_router(routes_jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(routes_ingest.router, prefix="/api/v1", tags=["ingest"])
app.include_router(routes_ticketing.router, prefix="/api/v1", tags=["ticketing"])
app.include_router(routes_ai_shield.router, prefix="/api/v1", tags=["internal-ai-shield"])
# Legacy incidents prefix for older dashboard calls
app.include_router(routes_incidents.router, prefix="/api/incidents", tags=["incidents-legacy"])
# Legacy agents prefixes for older dashboard calls
app.include_router(routes_agents.router, prefix="/api/agents", tags=["agents-legacy"])

# Direct legacy endpoints (no trailing slash) to avoid 404s when redirect_slashes is False
from app.api.routes_agents import get_agent_versions


@app.get("/api/agents")
def agents_legacy_root():
    """
    Legacy dashboard shape; the common identity gate still authenticates the caller.
    """
    return {"items": [], "total": 0}


@app.get("/api/agents/versions")
def agents_legacy_versions(tenant_id: str = Depends(get_current_tenant)):
    """
    Compatibility handler; earlier router precedence and fallbacks require route reconciliation.
    """
    return get_agent_versions(tenant_id=tenant_id)


@app.get("/")
def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "api-gateway"}


@app.get("/health")
def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": "0.1.0"
    }


def _metrics_response(format: str | None = None):
    if format == "prometheus":
        return PlainTextResponse(runtime_metrics.prometheus_text(), media_type=PROMETHEUS_MEDIA_TYPE)
    return runtime_metrics.snapshot()


@app.get("/metrics")
def metrics(format: str | None = None):
    """Lightweight runtime metrics for auth and readiness signals."""
    return _metrics_response(format)


@app.get("/metrics/prometheus")
def metrics_prometheus():
    """Prometheus exposition for production scraping."""
    return _metrics_response("prometheus")


async def _build_readiness_payload() -> dict:
    dependencies = await asyncio.gather(
        probe_http_dependency(
            "iam_agent",
            f"{settings.IAM_AGENT_URL}/health",
            verify_tls=settings.UPSTREAM_TLS_VERIFY,
            critical=True,
        ),
        probe_http_dependency(
            "orchestrator",
            f"{settings.ORCHESTRATOR_URL}/health",
            verify_tls=settings.UPSTREAM_TLS_VERIFY,
            critical=True,
        ),
    )
    return summarize_service_health("api-gateway", "0.1.0", dependencies)


@app.get("/ready")
async def ready():
    """Readiness contract for production orchestrations and load balancers."""
    payload = await _build_readiness_payload()
    runtime_metrics.record_readiness(payload)
    return JSONResponse(status_code=200 if payload["ready"] else 503, content=payload)


@app.on_event("startup")
def seed_tool_registry():
    """Seed tool registry from YAML when enabled."""
    flag = os.getenv("SEED_TOOL_REGISTRY", "false").lower()
    if flag not in ("1", "true", "yes", "on"):
        return
    try:
        inserted = run_seed()
        logger.info(f"Tool registry seed: inserted {inserted} new tool(s).")
    except Exception as exc:
        logger.warning(f"Tool registry seed failed: {exc}")
