import logging
from typing import List, Dict, Any, Optional

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class IngestClient:
    """
    Thin client to send batches to the unified SentinelGuard ingest endpoint.
    """

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = base_url or settings.INGEST_URL
        self.token = token or settings.INGEST_TOKEN

    def send_batch(self, tenant_id: str, agent_id: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not events:
            raise ValueError("events list is empty")

        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        payload = {
            "tenant_id": tenant_id,
            "agent_id": agent_id,
            "events": events,
        }

        resp = requests.post(self.base_url, json=payload, headers=headers, timeout=10)
        if not resp.ok:
            logger.error("Ingest request failed: status=%s body=%s", resp.status_code, resp.text)
            resp.raise_for_status()
        return resp.json()
