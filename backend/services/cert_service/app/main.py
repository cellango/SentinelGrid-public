"""Certificate Service - Main FastAPI application."""

import logging
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api import certificates, enrollment

# Add libs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SentinelGrid Certificate Service",
    description="Certificate issuance, renewal, and revocation service",
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
app.include_router(certificates.router, prefix="/api")
app.include_router(enrollment.router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Initializing database...")
    init_db()
    logger.info("Certificate Service started")


@app.get("/")
def root():
    """Health check."""
    return {"status": "ok", "service": "cert-service", "version": settings.VERSION}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION
    }
