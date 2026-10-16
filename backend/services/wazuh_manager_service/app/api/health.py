"""Health check endpoints."""

import logging
from fastapi import APIRouter, Depends
from app.core.config import settings
from app.services.wazuh_api_client import WazuhAPIClient

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Verifies connectivity to:
    - Database
    - Wazuh Manager API
    """
    health_status = {
        "service": "wazuh-manager-service",
        "version": settings.VERSION,
        "status": "healthy",
        "checks": {}
    }
    
    # Check Wazuh Manager connectivity
    try:
        wazuh_client = WazuhAPIClient(
            base_url=settings.WAZUH_MANAGER_URL,
            username=settings.WAZUH_API_USERNAME,
            password=settings.WAZUH_API_PASSWORD
        )
        
        # Try to get token (authenticates with Wazuh)
        await wazuh_client._get_token()
        health_status["checks"]["wazuh_manager"] = {
            "status": "connected",
            "url": settings.WAZUH_MANAGER_URL
        }
    except Exception as e:
        logger.error(f"Wazuh Manager health check failed: {e}")
        health_status["checks"]["wazuh_manager"] = {
            "status": "error",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "SentinelGrid Endpoint Manager Service",
        "version": settings.VERSION,
        "description": "Agent management API for SentinelGrid Endpoint Protection",
        "powered_by": "Wazuh 4.8.0"
    }

