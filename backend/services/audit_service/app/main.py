"""Audit Service - Main FastAPI application."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import audit_logs, retention

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="SentinelGrid Audit Service",
    description="Centralized audit logging and retention management for compliance",
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
app.include_router(audit_logs.router, prefix="/api/v1/audit", tags=["audit-logs"])
app.include_router(retention.router, prefix="/api/v1/audit/retention", tags=["retention"])


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
