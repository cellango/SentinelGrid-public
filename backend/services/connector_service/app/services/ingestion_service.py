"""Service for sending events to ingestion service."""

import logging
import httpx
from typing import List, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


def send_to_ingestion(tenant_id: str, events: List[Dict[str, Any]]) -> None:
    """
    Send events to ingestion service.
    
    Args:
        tenant_id: Tenant ID
        events: List of event dictionaries
    """
    url = f"{settings.INGESTION_SERVICE_URL}/ingest/events"
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                json={
                    "events": events,
                    "tenant_id": tenant_id,
                },
                headers={
                    "Authorization": f"Bearer {settings.INTERNAL_SERVICE_TOKEN}",
                    "X-Tenant-ID": tenant_id,
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            logger.info(f"Successfully sent {len(events)} events to ingestion service")
    
    except Exception as e:
        logger.error(f"Failed to send events to ingestion service: {e}")
        raise

