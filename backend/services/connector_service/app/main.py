"""Connector Service - Main application."""

import logging
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.security import require_connector_request
from app.api import connectors

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Schema ownership and upgrades require a reviewed Flyway profile; no import-time DDL.

app = FastAPI(
    title="SentinelGrid Connector Service",
    description="Identity and Cloud connector service",
    version=settings.VERSION,
    dependencies=[Depends(require_connector_request)],
)

app.state.iam_verification_settings = settings.verification_settings()
app.state.connector_principal_settings = settings.principal_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(connectors.router, prefix="/api/v1")
app.include_router(connectors.oauth_router, prefix="/api/v1")


@app.get("/")
def root():
    """Health check."""
    return {"status": "ok", "service": "connector-service"}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION
    }
