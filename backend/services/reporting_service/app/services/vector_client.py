"""Vector client to index reports for tenant-scoped RAG."""

import logging
import os
import httpx
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class VectorClient:
    def __init__(self):
        self.model_gateway_url = os.getenv("MODEL_GATEWAY_URL", "http://model_gateway:8000")
        self.internal_token = os.getenv("INTERNAL_SERVICE_TOKEN", "")

    async def index_report(
        self,
        tenant_id: str,
        realm_name: str,
        report_id: str,
        template_id: str,
        template_name: str,
        file_path: str,
        sections: List[Dict[str, Any]],
    ) -> None:
        """
        Push report content/metadata into the model gateway KB for tenant-scoped retrieval.
        """
        url = f"{self.model_gateway_url}/internal/llm/knowledge-base/load/report"
        headers = {"Content-Type": "application/json"}
        if self.internal_token:
            headers["Authorization"] = f"Bearer {self.internal_token}"

        payload = {
            "tenant_id": tenant_id,
            "realm_name": realm_name,
            "report_id": report_id,
            "template_id": template_id,
            "template_name": template_name,
            "file_path": file_path,
            "sections": sections,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
