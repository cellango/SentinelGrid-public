"""Audit client for reporting service."""

import logging
import os
from typing import Dict, Any

import httpx

logger = logging.getLogger(__name__)


class AuditClient:
    def __init__(self):
        self.audit_service_url = os.getenv("AUDIT_SERVICE_URL", "http://audit_service:8000")
        self.token = os.getenv("INTERNAL_SERVICE_TOKEN", "")

    async def log_event(self, payload: Dict[str, Any]) -> None:
        """Send a generic audit event to the audit service."""
        url = f"{self.audit_service_url}/api/v1/audit/logs"
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(url, json=payload, headers=headers)
        except Exception as e:
            logger.warning(f"Failed to log audit event: {e}")
