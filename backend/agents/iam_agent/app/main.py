"""IAM Agent Service - Identity and access management."""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from app.core.config import settings
from app.core.database import engine as db_engine
from app.api import auth, ai_chat, ai_features, automation, compliance, audit, protocols, sync_jobs, mfa, stats, payment, onboarding, agents, hardened_images, git_providers, git_scanning, iam_portal, leads, marketing, dashboard, realms, iam_orgs
from app.api import policies as iam_policies
# New IAM APIs (Dec 3, 2025 - 100% Implementation) - TEMPORARILY COMMENTED OUT
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
from app.services.keycloak_seeder import KeycloakSeeder, SeedingResult
from app.services.keycloak_admin_client import KeycloakAdminClient
from app.services.lifecycle_scheduler import start_scheduler, stop_scheduler
from app.middleware.security import RateLimitMiddleware, SecurityHeadersMiddleware
from app.middleware.admin_audit import AdminAuditMiddleware
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

# Global seeding result
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting IAM Agent service...")
    
    # Run Keycloak seeding in background
    global seeding_result
    seeder = KeycloakSeeder()
    
    # Run seeding asynchronously (don't block startup)
    async def run_seeding():
        global seeding_result
        try:
            seeding_result = await seeder.seed_all()
        except Exception as e:
            logger.error(f"Error during Keycloak seeding: {e}", exc_info=True)
            seeding_result = None
    
    # Start seeding task
    seeding_task = asyncio.create_task(run_seeding())
    # Start lifecycle scheduler (non-blocking)
    start_scheduler()
    
    yield
    
    # Shutdown
    logger.info("Shutting down IAM Agent service...")
    # Cancel seeding task if still running
    if not seeding_task.done():
        seeding_task.cancel()
        try:
            await seeding_task
        except asyncio.CancelledError:
            pass
    # Stop lifecycle scheduler
    await stop_scheduler()


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
app.add_middleware(AdminAuditMiddleware)

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

# Include routers
app.include_router(auth.router)  # Internal: /internal/iam/auth/*
app.include_router(auth.public_router)  # Public: /api/v1/auth/*

# New IAM APIs (Dec 3, 2025) - TEMPORARILY COMMENTED OUT (need Docker rebuild)
# app.include_router(users.router)  # User management
# app.include_router(roles.router)  # Role management
# app.include_router(mfa_totp.router)  # TOTP MFA
# app.include_router(audit_logs.router)  # Audit log queries

# Existing routers
app.include_router(ai_chat.router)
app.include_router(ai_features.router)
app.include_router(automation.router)
app.include_router(compliance.router)
app.include_router(audit.router)
app.include_router(protocols.router)
app.include_router(sync_jobs.router)
app.include_router(mfa.router)  # Legacy MFA (biometric/adaptive)
app.include_router(stats.router)
app.include_router(payment.router)
app.include_router(leads.router)
app.include_router(marketing.router)
app.include_router(marketing.internal_router)
app.include_router(onboarding.router)
app.include_router(onboarding.portal_router)
app.include_router(agents.router)
app.include_router(hardened_images.router)
app.include_router(git_providers.router)
app.include_router(git_scanning.router)
app.include_router(iam_portal.router)
app.include_router(iam_orgs.router)
app.include_router(dashboard.router, prefix="/api/v1/iam")
app.include_router(iam_policies.router)
app.include_router(realms.router)  # Realm creation API - CRITICAL: All realm creation must go through this

# Entitlement routers (merged from entitlement_agent - Dec 3, 2025)
app.include_router(bulk_operations.router)
app.include_router(entitlements.router)
app.include_router(role_mappings.router)
app.include_router(authorize.router)
app.include_router(governance.router)
app.include_router(access_requests.router)

# Phase 1: User Lifecycle & Self-Service
app.include_router(user_onboarding.router)
app.include_router(organization.router)
app.include_router(self_service.router)

# Phase 2: Authentication Enhancements
app.include_router(passwordless.router)
app.include_router(webauthn.router)
app.include_router(adaptive_auth.router)

# Phase 3: SSO & App Catalog
app.include_router(app_catalog.router)
app.include_router(app_catalog.portal_router)
app.include_router(app_assignments.router)
app.include_router(apps.router)
app.include_router(external_idp.router)
app.include_router(scim.router)

# Phase 4: Device & Endpoint Security
app.include_router(devices.router)
app.include_router(mdm.router)

# Phase 5: Threat Protection & Analytics
app.include_router(anomalies.router)
app.include_router(itdr.router)
app.include_router(nhi.router)
app.include_router(reports.router)

# Phase 6: Advanced Features
app.include_router(privileged_access.router)
app.include_router(secrets.router)
app.include_router(ztna.router)
app.include_router(api_keys.router)
app.include_router(gateway.router)
app.include_router(state.router)


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
