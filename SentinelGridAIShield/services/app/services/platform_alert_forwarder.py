"""Forward risky AI Shield telemetry into the main SentinelGrid platform workflow."""

from __future__ import annotations

import logging

import httpx

from app import schemas
from app.core.config import settings

logger = logging.getLogger(__name__)


def forward_event_to_platform(event: schemas.TelemetryEventCreate) -> dict | None:
    """Send a normalized AI event to the main SentinelGrid internal ingest endpoint."""
    if not settings.PLATFORM_ALERT_INGEST_ENABLED:
        return None

    base_url = settings.PLATFORM_API_URL.rstrip("/")
    path = settings.PLATFORM_ALERT_INGEST_PATH
    url = f"{base_url}{path}"
    payload = event.model_dump(mode="json", exclude_none=True)

    headers = {
        "Authorization": f"Bearer {settings.INTERNAL_SERVICE_TOKEN}",
        "X-Tenant-ID": str(event.org_id),
        "Content-Type": "application/json",
    }

    response = httpx.post(
        url,
        json=payload,
        headers=headers,
        timeout=settings.PLATFORM_ALERT_INGEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    if response.content:
        return response.json()
    return None
