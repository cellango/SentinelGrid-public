"""IAM Agent Service - Identity and access management."""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from app.core.source_admission import include_source_router, source_review_lifespan
from app.core.config import settings
from app.core.database import engine as db_engine
from app.api import auth, ai_chat, ai_features, automation, compliance, audit, protocols, sync_jobs, mfa, stats, payment, onboarding, agents, hardened_images, git_providers, git_scanning, iam_portal, leads, marketing, dashboard, realms, iam_orgs
from app.api import ai_editor
from app.api import policies as iam_policies
# Additional legacy IAM API source (not admitted)
# from app.api import users, roles, mfa_totp, audit_logs
# Entitlement functionality (merged from entitlement_agent Dec 3, 2025)
from app.api import entitlements, bulk_operations, role_mappings, authorize, governance, access_requests
# Phase 1: User Lifecycle & Self-Service
from app.api import user_onboarding, organization, self_service
# Phase 2: Authentication Enhancements
from app.api import passwordless, webauthn, adaptive_auth
# Phase 3: SSO & App Catalog
from app.api import app_catalog, app_assignments, apps, external_idp, scim
# Phase 4: Device & Endpoint Security
from app.api import devices, mdm
# Phase 5: Threat Protection & Analytics
from app.api import anomalies, reports, itdr, nhi
# Phase 6: Advanced Features
from app.api import privileged_access, secrets, ztna, api_keys
from app.api import gateway
from app.api import state
from app.services.keycloak_admin_client import KeycloakAdminClient
from app.middleware.security import RateLimitMiddleware, SecurityHeadersMiddleware
from sg_core.request_tracing import RequestTracingMiddleware, configure_logging
from sg_core.service_health import (
    build_dependency_status,
    probe_database_engine_async,
    summarize_service_health,
)
from sg_core.service_metrics import get_service_metrics

logger = configure_logging(settings.SERVICE_NAME)
runtime_metrics = get_service_metrics(settings.SERVICE_NAME)
PROMETHEUS_MEDIA_TYPE = "text/plain; version=0.0.4; charset=utf-8"

# Legacy readiness metadata; automatic seeding is unavailable
seeding_result = None


async def _probe_database_dependency() -> dict:
    return await probe_database_engine_async("database", db_engine, critical=True)


async def _probe_keycloak_dependency() -> dict:
    client = KeycloakAdminClient()
    try:
        health = await client.health_check()
        status = "healthy" if health.get("status") == "healthy" else "unhealthy"
        detail = health.get("error") or health.get("status") or "unknown"
        return build_dependency_status(
            "keycloak_admin",
            status=status,
            critical=True,
            detail=detail,
            url=health.get("keycloak_url"),
            extra={
                "admin_authenticated": bool(health.get("admin_authenticated")),
                "token_cached": bool(health.get("token_cached")),
            },
        )
    except Exception as exc:
        return build_dependency_status(
            "keycloak_admin",
            status="unhealthy",
            critical=True,
            detail=str(exc),
            url=settings.KEYCLOAK_URL,
        )
    finally:
        await client.close()


async def _build_readiness_payload() -> dict:
    dependencies = await asyncio.gather(
        _probe_database_dependency(),
        _probe_keycloak_dependency(),
    )
    extra = {}
    if seeding_result:
        extra["seeding"] = seeding_result.to_dict()
    return summarize_service_health(settings.SERVICE_NAME, settings.VERSION, dependencies, extra=extra)


lifespan = source_review_lifespan


# Create FastAPI app with lifespan
app = FastAPI(
    title="SentinelGrid IAM Agent",
    description="Identity and Access Management service with Keycloak integration",
    version=settings.VERSION,
    lifespan=lifespan
)

# Security middleware (must be first)
app.add_middleware(SecurityHeadersMiddleware)

# Audit middleware (non-blocking)
# Domain handlers own durable audit. Do not install the unqualified best-effort
# middleware that can initialize a legacy provider/store before a route is denied.

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware, redis_client=None)  # TODO: Add Redis client if available

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestTracingMiddleware, service_name=settings.SERVICE_NAME)

# Explicit bounded source operations register before blocked legacy aliases.
include_source_router(app, 'auth.router', auth.router)
include_source_router(app, 'auth.public_router', auth.public_router)
include_source_router(app, 'bulk_operations.router', bulk_operations.router)
include_source_router(app, 'entitlements.router', entitlements.router)
include_source_router(app, 'role_mappings.router', role_mappings.router)
include_source_router(app, 'authorize.router', authorize.router)
include_source_router(app, 'governance.router', governance.router)
include_source_router(app, 'access_requests.router', access_requests.router)
include_source_router(app, 'iam_policies.router', iam_policies.router)
include_source_router(app, 'ai_editor.router', ai_editor.router)
include_source_router(app, 'scim.router', scim.router)
include_source_router(app, 'itdr.router', itdr.router)
include_source_router(app, 'nhi.router', nhi.router)
include_source_router(app, 'ai_chat.router', ai_chat.router)
include_source_router(app, 'ai_features.router', ai_features.router)
include_source_router(app, 'automation.router', automation.router)
include_source_router(app, 'compliance.router', compliance.router)
include_source_router(app, 'audit.router', audit.router)
include_source_router(app, 'protocols.router', protocols.router)
include_source_router(app, 'sync_jobs.router', sync_jobs.router)
include_source_router(app, 'mfa.router', mfa.router)
include_source_router(app, 'stats.router', stats.router)
include_source_router(app, 'payment.router', payment.router)
include_source_router(app, 'leads.router', leads.router)
include_source_router(app, 'marketing.router', marketing.router)
include_source_router(app, 'marketing.internal_router', marketing.internal_router)
include_source_router(app, 'onboarding.router', onboarding.router)
include_source_router(app, 'onboarding.portal_router', onboarding.portal_router)
include_source_router(app, 'agents.router', agents.router)
include_source_router(app, 'hardened_images.router', hardened_images.router)
include_source_router(app, 'git_providers.router', git_providers.router)
include_source_router(app, 'git_scanning.router', git_scanning.router)
include_source_router(app, 'iam_portal.router', iam_portal.router)
include_source_router(app, 'iam_orgs.router', iam_orgs.router)
include_source_router(app, 'dashboard.router', dashboard.router, prefix='/api/v1/iam')
include_source_router(app, 'realms.router', realms.router)
include_source_router(app, 'user_onboarding.router', user_onboarding.router)
include_source_router(app, 'organization.router', organization.router)
include_source_router(app, 'self_service.router', self_service.router)
include_source_router(app, 'passwordless.router', passwordless.router)
include_source_router(app, 'webauthn.router', webauthn.router)
include_source_router(app, 'adaptive_auth.router', adaptive_auth.router)
include_source_router(app, 'app_catalog.router', app_catalog.router)
include_source_router(app, 'app_catalog.portal_router', app_catalog.portal_router)
include_source_router(app, 'app_assignments.router', app_assignments.router)
include_source_router(app, 'apps.router', apps.router)
include_source_router(app, 'external_idp.router', external_idp.router)
include_source_router(app, 'devices.router', devices.router)
include_source_router(app, 'mdm.router', mdm.router)
include_source_router(app, 'anomalies.router', anomalies.router)
include_source_router(app, 'reports.router', reports.router)
include_source_router(app, 'privileged_access.router', privileged_access.router)
include_source_router(app, 'secrets.router', secrets.router)
include_source_router(app, 'ztna.router', ztna.router)
include_source_router(app, 'api_keys.router', api_keys.router)
include_source_router(app, 'gateway.router', gateway.router)
include_source_router(app, 'state.router', state.router)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "iam-agent",
        "version": settings.VERSION,
        "status": "running"
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    from app.services.keycloak_client import KeycloakClient
    
    keycloak_client = KeycloakClient()
    jwks_url = keycloak_client.get_public_key()
    
    # Include seeding status
    seeding_status = None
    if seeding_result:
        seeding_status = seeding_result.to_dict()
    
    return {
        "status": "healthy",
        "service": "iam-agent",
        "version": settings.VERSION,
        "keycloak": {
            "url": settings.KEYCLOAK_URL,
            "realm": settings.KEYCLOAK_REALM,
            "connected": jwks_url is not None
        },
        "seeding": seeding_status
    }


def _metrics_response(format: str | None = None):
    if format == "prometheus":
        return PlainTextResponse(runtime_metrics.prometheus_text(), media_type=PROMETHEUS_MEDIA_TYPE)
    return runtime_metrics.snapshot()


@app.get("/metrics")
async def metrics(format: str | None = None):
    """Lightweight runtime metrics for readiness and auth flows."""
    return _metrics_response(format)


@app.get("/metrics/prometheus")
async def metrics_prometheus():
    """Prometheus exposition for production scraping."""
    return _metrics_response("prometheus")


@app.get("/ready")
async def ready():
    """Readiness contract for production traffic and lifecycle automation."""
    payload = await _build_readiness_payload()
    runtime_metrics.record_readiness(payload)
    return JSONResponse(status_code=200 if payload["ready"] else 503, content=payload)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
