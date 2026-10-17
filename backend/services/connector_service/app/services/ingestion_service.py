"""Event delivery requires the owned ingestion workload and acceptance contract."""

from typing import Any


def send_to_ingestion(tenant_id: str, events: list[dict[str, Any]]) -> None:
    """Legacy caller cannot promote a static token plus tenant/body into authority.

    Retain real delivery as required restoration work; never report fake success.
    No credentials, event data or network destination are used by this guard.
    """
    raise RuntimeError("Owned ingestion workload and delivery contract required")
