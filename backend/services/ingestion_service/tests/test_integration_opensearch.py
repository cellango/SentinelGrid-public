import asyncio
import os

import httpx
import pytest
from datetime import datetime, timezone

from app.services.batch_processor import BatchProcessor
from app.models.event import IngestEvent, ECSField


def opensearch_url():
    return os.getenv("OPENSEARCH_URL", "http://localhost:9200")


def is_opensearch_up(url: str) -> bool:
    try:
        resp = httpx.get(f"{url}/_cluster/health", timeout=2.5)
        return resp.status_code == 200
    except Exception:
        return False


@pytest.mark.integration
def test_send_to_opensearch_creates_docs():
    url = opensearch_url()
    if not is_opensearch_up(url):
        pytest.skip("OpenSearch not reachable; set OPENSEARCH_URL or start local cluster")

    tenant_id = "itest-tenant"
    index = f"{tenant_id}-logs"

    bp = BatchProcessor()
    bp.opensearch_url = url

    events = [
        IngestEvent(
          ecs_fields=ECSField(
              **{
                  "@timestamp": datetime.now(timezone.utc),
                  "tenant_id": tenant_id,
                  "event_type": "process",
                  "source": {"name": "openedr", "type": "endpoint"},
                  "edr_source": "sentinelguard-openedr",
                  "sidecar_enabled": True,
              }
          ),
          raw_data={"source": "openedr"},
        )
    ]

    asyncio.run(bp._send_to_opensearch(tenant_id, events))

    # Verify docs landed
    resp = httpx.get(f"{url}/{index}/_count", timeout=3.0)
    resp.raise_for_status()
    count = resp.json().get("count", 0)
    assert count >= 1

    # Cleanup test index
    httpx.delete(f"{url}/{index}", timeout=3.0)
