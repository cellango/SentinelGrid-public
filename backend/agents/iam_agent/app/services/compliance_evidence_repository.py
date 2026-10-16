"""Client for writing IAM evidence into the Compliance evidence repository."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ComplianceEvidenceRepositoryClient:
    """Thin HTTP client for Compliance Service durable evidence APIs."""

    def __init__(
        self,
        tenant_id: str,
        authorization_header: str | None,
        actor_id: str | None = None,
        service_url: str | None = None,
        timeout_seconds: float = 8.0,
    ):
        self.tenant_id = tenant_id
        self.authorization_header = authorization_header
        self.actor_id = actor_id
        self.service_url = (service_url or settings.COMPLIANCE_SERVICE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def create_evidence_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/api/v1/compliance/evidence", payload)

    def create_collection_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/api/v1/compliance/evidence/tasks", payload)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.authorization_header:
            raise RuntimeError("Authorization header is required to persist compliance evidence")

        request_payload = dict(payload)
        request_payload["tenant_id"] = self.tenant_id
        headers = {
            "Authorization": self.authorization_header,
            "X-Tenant-ID": self.tenant_id,
            "Content-Type": "application/json",
        }
        if self.actor_id:
            headers["X-User-ID"] = self.actor_id

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.service_url}{path}",
                headers=headers,
                json=request_payload,
            )
            if response.status_code >= 400:
                logger.warning(
                    "Compliance evidence repository write failed",
                    extra={
                        "path": path,
                        "status_code": response.status_code,
                        "tenant_id": self.tenant_id,
                    },
                )
            response.raise_for_status()
            return response.json()
