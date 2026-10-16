"""
Metadata Service - Consolidated CRUD operations

Consolidates:
- cmdb_service (asset inventory)
- vulnerability_service (CVE tracking)
- incident_service (NIST workflow)
- tenant_service (tenant management)

Created: Dec 3, 2025 - Service Consolidation Phase
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import assets, vulnerabilities, incidents, tenants

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SentinelGrid Metadata Service",
    description="Unified metadata management - Assets, Vulnerabilities, Incidents, Tenants",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(assets.router, prefix="/api/v1/metadata/assets", tags=["assets"])
app.include_router(vulnerabilities.router, prefix="/api/v1/metadata/vulnerabilities", tags=["vulnerabilities"])
app.include_router(incidents.router, prefix="/api/v1/metadata/incidents", tags=["incidents"])
app.include_router(tenants.router, prefix="/api/v1/metadata/tenants", tags=["tenants"])


@app.get("/")
def root():
    """Health check."""
    return {
        "status": "ok",
        "service": "metadata-service",
        "version": "1.0.0",
        "modules": ["assets", "vulnerabilities", "incidents", "tenants"]
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
