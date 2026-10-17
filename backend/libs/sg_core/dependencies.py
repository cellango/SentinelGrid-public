"""Service-scoped dependencies; a caller-supplied tenant header is not authority."""

from functools import lru_cache
from uuid import UUID
from fastapi import Header, HTTPException, Request
from sg_core.workload_reads import get_workload_read_context, service_audience


async def get_current_tenant(x_tenant_id: str | None = Header(None), request: Request = None) -> UUID:
    """Legacy unscoped import retained as an explicit unavailable boundary."""
    raise HTTPException(503, "Service-scoped caller policy is required")


@lru_cache(maxsize=3)
def service_tenant_dependency(service_id: str):
    """Server-selected service identity. No request/env/body-selected target."""
    service_audience(service_id)  # Reject unknown adapters before dependency creation.

    def get_tenant(request: Request) -> UUID:
        return get_workload_read_context(request, service_id).tenant_id

    return get_tenant
