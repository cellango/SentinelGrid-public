"""
OPA helper: build input and enforce allow via OPA data.sentinelgrid.authz.allow.
"""

import os
import logging
import httpx
from typing import Any, Dict, Optional
from fastapi import HTTPException, Depends, Request

from sg_core.security import get_current_payload

logger = logging.getLogger(__name__)

OPA_URL = os.getenv("OPA_URL", "http://opa:8181/v1/data/sentinelgrid/authz/allow")
# Comma-separated list of path prefixes that should bypass OPA (dev/health helpers).
OPA_SKIP_PATHS = [
    p.strip()
    for p in os.getenv(
        "OPA_SKIP_PATHS",
        "/api/siem/source-health,/api/siem/ingestion/load-sample,"
        "/api/v1/siem/source-health,/api/v1/siem/ingestion/load-sample",
    ).split(",")
    if p.strip()
]


def build_opa_input(
    payload: Dict[str, Any],
    request: Request,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
) -> Dict[str, Any]:
    path_parts = [p for p in request.url.path.split("/") if p]
    inferred_type = resource_type or (path_parts[2] if len(path_parts) > 2 else "unknown")
    return {
        "tenant_id": payload.get("tenant_id"),
        "user": {
            "id": payload.get("user_id"),
            "roles": payload.get("roles", []),
            "groups": payload.get("groups", []),
            "email": payload.get("email"),
        },
        "request": {
            "service": "api-gateway",
            "path": request.url.path,
            "method": request.method,
        },
        "resource": {
            "type": inferred_type,
            "id": resource_id,
            "owner_tenant": payload.get("tenant_id"),
        },
        "context": {
            "client": "api-gateway",
            "plan_tier": payload.get("plan_tier"),
        },
    }


async def opa_allow(input_obj: Dict[str, Any]) -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(OPA_URL, json={"input": input_obj})
            resp.raise_for_status()
            data = resp.json()
            # Accept either boolean result or {"allow": bool}
            result = data.get("result")
            if isinstance(result, dict):
                return bool(result.get("allow"))
            return bool(result)
    except httpx.HTTPStatusError as e:
        logger.error(f"OPA HTTP error: {e}")
        raise HTTPException(status_code=503, detail="OPA decision unavailable")
    except Exception as e:
        logger.error(f"OPA call failed: {e}")
        raise HTTPException(status_code=503, detail="OPA decision unavailable")


async def require_opa_allow(
    request: Request,
    payload: dict = Depends(get_current_payload),
):
    # Allow certain dev/health endpoints to bypass OPA (e.g., seeding helpers).
    for prefix in OPA_SKIP_PATHS:
        if request.url.path.startswith(prefix):
            logger.info("OPA bypass for path %s via prefix %s", request.url.path, prefix)
            return

    logger.debug("OPA enforcing for path %s", request.url.path)
    input_obj = build_opa_input(payload, request)
    allowed = await opa_allow(input_obj)
    if not allowed:
        raise HTTPException(status_code=403, detail="Access denied by policy")
