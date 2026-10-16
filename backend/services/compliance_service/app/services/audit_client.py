"""Best-effort audit client for compliance-service lifecycle events."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


class AuditClient:
    """Send compliance audit events without making request handling depend on audit availability."""

    def __init__(self) -> None:
        self.audit_service_url = getattr(settings, "AUDIT_SERVICE_URL", "http://audit_service:8000")
        self.token = getattr(settings, "INTERNAL_SERVICE_TOKEN", "")

    async def log_event(self, payload: dict[str, Any]) -> None:
        url = f"{self.audit_service_url.rstrip('/')}/api/v1/audit/logs"
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(url, json=payload, headers=headers)
        except Exception as exc:  # pragma: no cover - audit must never block evidence workflows.
            logger.warning("Failed to log compliance audit event: %s", exc)
