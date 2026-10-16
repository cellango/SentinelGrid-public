"""HTTP clients for internal microservices."""

import logging
from typing import Dict, Any, Optional
import httpx

from app.core.config import settings
from sg_core.service_security import build_internal_auth_headers

logger = logging.getLogger(__name__)


class ServiceClients:
    """Centralized HTTP clients for all internal microservices."""
    
    def __init__(self):
        """Initialize HTTP clients for each service."""
        headers = build_internal_auth_headers(
            settings.INTERNAL_SERVICE_TOKEN,
            extra_headers={"Content-Type": "application/json"},
        )
        
        self.siem_agent = httpx.AsyncClient(
            base_url=settings.SIEM_AGENT_URL,
            headers=headers,
            timeout=30.0
        )
        
        self.soar_agent = httpx.AsyncClient(
            base_url=settings.SOAR_AGENT_URL,
            headers=headers,
            timeout=30.0
        )
        
        self.iam_agent = httpx.AsyncClient(
            base_url=settings.IAM_AGENT_URL,
            headers=headers,
            timeout=30.0
        )
        
        self.posture_agent = httpx.AsyncClient(
            base_url=settings.POSTURE_AGENT_URL,
            headers=headers,
            timeout=30.0
        )
        
        self.observables_service = httpx.AsyncClient(
            base_url=settings.OBSERVABLES_SERVICE_URL,
            headers=headers,
            timeout=30.0
        )
        
        self.detection_service = httpx.AsyncClient(
            base_url=settings.DETECTION_SERVICE_URL,
            headers=headers,
            timeout=30.0
        )
        
        self.compliance_service = httpx.AsyncClient(
            base_url=settings.COMPLIANCE_SERVICE_URL,
            headers=headers,
            timeout=30.0
        )
        
        self.vulnerability_service = httpx.AsyncClient(
            base_url=settings.VULNERABILITY_SERVICE_URL,
            headers=headers,
            timeout=30.0
        )
        
        self.ticketing_agent = httpx.AsyncClient(
            base_url=settings.TICKETING_AGENT_URL,
            headers=headers,
            timeout=30.0
        )
        
        self.framework_service = httpx.AsyncClient(
            base_url=settings.FRAMEWORK_SERVICE_URL,
            headers=headers,
            timeout=30.0
        )
    
    async def close_all(self):
        """Close all HTTP clients."""
        await self.siem_agent.aclose()
        await self.soar_agent.aclose()
        await self.iam_agent.aclose()
        await self.posture_agent.aclose()
        await self.observables_service.aclose()
        await self.detection_service.aclose()
        await self.compliance_service.aclose()
        await self.vulnerability_service.aclose()
        await self.ticketing_agent.aclose()
        await self.framework_service.aclose()
    
    def add_tenant_header(self, tenant_id: str) -> Dict[str, str]:
        """Get headers with tenant ID."""
        return {"X-Tenant-ID": tenant_id}


# Global service clients instance
clients = ServiceClients()
