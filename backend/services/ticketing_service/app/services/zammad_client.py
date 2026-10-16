"""Zammad client for ticket create/update."""

import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


class ZammadClient:
    """Lightweight Zammad REST client."""

    def __init__(
        self,
        base_url: str,
        token: str,
        group: str,
        priority_map: Dict[str, str],
        verify_tls: bool,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.group = group
        self.priority_map = priority_map
        self.verify_tls = verify_tls

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Token token={self.token}",
            "Content-Type": "application/json",
        }

    def _map_priority(self, severity: Optional[str]) -> str:
        if not severity:
            return self.priority_map.get("medium", "2")
        return self.priority_map.get(severity.lower(), self.priority_map.get("medium", "2"))

    async def create_ticket(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create ticket in Zammad; returns ticket JSON or None."""
        try:
            async with httpx.AsyncClient(timeout=30.0, verify=self.verify_tls) as client:
                resp = await client.post(f"{self.base_url}/api/v1/tickets", json=payload, headers=self._headers())
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Zammad create_ticket failed: {e}")
            return None

    async def update_ticket(self, ticket_id: int, payload: Dict[str, Any]) -> bool:
        """Update ticket in Zammad."""
        try:
            async with httpx.AsyncClient(timeout=30.0, verify=self.verify_tls) as client:
                resp = await client.put(f"{self.base_url}/api/v1/tickets/{ticket_id}", json=payload, headers=self._headers())
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Zammad update_ticket failed: {e}")
            return False

    def build_payload(
        self,
        title: str,
        description: str,
        severity: Optional[str],
        tenant_id: str,
        alert_ids: Optional[list] = None,
        incident_id: Optional[str] = None,
        custom: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Map our ticket to Zammad fields with custom metadata."""
        meta = custom or {}
        if alert_ids:
            meta["sg_alert_ids"] = alert_ids
        if incident_id:
            meta["sg_incident_id"] = incident_id
        meta["sg_tenant_id"] = tenant_id

        return {
            "title": title,
            "group": self.group,
            "priority_id": self._map_priority(severity),
            "article": {
                "subject": title,
                "body": description or title,
                "type": "note",
              },
            "tags": [tenant_id, "sg"],
            "customer_id": None,
            "custom": meta,
        }
