"""Lightweight audit client for AI actions."""

import logging
from typing import Dict, Any
import httpx
import os

logger = logging.getLogger(__name__)


class AuditClient:
    def __init__(self):
        self.audit_service_url = os.getenv("AUDIT_SERVICE_URL", "http://audit_service:8000")
        self.token = os.getenv("INTERNAL_SERVICE_TOKEN", "")

    async def log_ai_event(self, payload: Dict[str, Any]) -> None:
        """Send an AI audit event to the audit service."""
        url = f"{self.audit_service_url}/api/v1/audit/ai-activity"
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(url, json=payload, headers=headers)
        except Exception as e:
            logger.warning(f"Failed to log AI audit event: {e}")
