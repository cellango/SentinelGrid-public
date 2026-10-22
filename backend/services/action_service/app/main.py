"""Action Agent Service - Automated security actions."""

import logging
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import actions

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

from sg_core.http_ingress import GatewayIngressMiddleware, IngressPolicy
from sg_core.action_identity import require_actor
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.user_principals import UserPrincipalSettings


def admission(request: Request):
    if (request.method, request.url.path) in {("GET", "/"), ("GET", "/health")}:
        return
    return require_actor(request)


app = FastAPI(
    title="SentinelGrid Action Agent",
    description="Automated security actions service",
    dependencies=[Depends(admission)],
    version=settings.VERSION,
)

app.state.iam_verification_settings = IAMVerificationSettings()
app.state.user_principal_settings = UserPrincipalSettings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    GatewayIngressMiddleware,
    policy=IngressPolicy(
        allowed_origins=(), max_body_bytes=32768, max_concurrent_requests=16
    ),
)

# Include routers
app.include_router(actions.router, prefix="/api/v1/actions", tags=["actions"])


@app.get("/")
def root():
    """Health check."""
    return {"status": "ok", "service": "action-agent"}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
    }
