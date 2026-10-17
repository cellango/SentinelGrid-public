"""
SentinelGrid Endpoint Manager Service

Main application for managing SentinelGrid Endpoint Protection agents.
Integrates with Wazuh Manager 4.8.0 for endpoint security.
"""

import logging
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.security import require_wazuh_request
from app.api import agents, health

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SentinelGrid Endpoint Manager Service",
    description="Agent management API for SentinelGrid Endpoint Protection (powered by Wazuh 4.8.0)",
    dependencies=[Depends(require_wazuh_request)],
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.iam_verification_settings = settings.verification_settings()
app.state.wazuh_principal_settings = settings.principal_settings()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(agents.router, prefix="/api/v1/wazuh")


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info("=" * 60)
    logger.info("SentinelGrid Endpoint Manager Service Starting")
    logger.info(f"Version: {settings.VERSION}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("SentinelGrid Endpoint Manager Service Shutting Down")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
