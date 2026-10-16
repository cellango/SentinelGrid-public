"""Agent management routes."""

from typing import Any

import httpx
from fastapi import APIRouter, Depends
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

from sg_core.security import get_current_tenant
from app.core.config import settings

router = APIRouter()


@router.get("/")
def list_agents(
    tenant_id: str = Depends(get_current_tenant),
):
    """List runtime, service, and endpoint/customer agents."""
    runtime_items, runtime_diagnostics = _runtime_agent_inventory(tenant_id)
    endpoint_items, endpoint_diagnostics = _endpoint_agent_inventory(tenant_id)
    items = runtime_items + _service_agent_inventory() + endpoint_items
    return {
        "items": items,
        "total": len(items),
        "diagnostics": {**runtime_diagnostics, **endpoint_diagnostics},
    }


@router.get("/diagnostics")
def get_agent_diagnostics(
    tenant_id: str = Depends(get_current_tenant),
):
    """Return admin-facing diagnostics for agent inventory sources."""
    runtime_items, runtime_diagnostics = _runtime_agent_inventory(tenant_id)
    ready_diagnostics = _runtime_ready_diagnostics(tenant_id)
    _versions_payload, endpoint_diagnostics = _fetch_iam_agent_versions(tenant_id)
    return {
        "agent_runtime": {
            **runtime_diagnostics,
            "ready": ready_diagnostics,
            "runtime_agent_counts": _runtime_status_counts(runtime_items),
        },
        "endpoint_packages": endpoint_diagnostics,
    }


@router.get("/versions")
def get_agent_versions(
    tenant_id: str = Depends(get_current_tenant),
):
    """Get available agent versions."""
    if tenant_id == "legacy-dashboard":
        return _fallback_agent_versions_response()
    versions_payload, _diagnostics = _fetch_iam_agent_versions(tenant_id)
    if versions_payload:
        return _agent_versions_response(versions_payload)
    return _fallback_agent_versions_response()


def _runtime_agent_inventory(tenant_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    diagnostics = {
        "agent_runtime_url": settings.AGENT_RUNTIME_URL,
        "agent_runtime_status": "unknown",
        "feature_flags": {},
        "warning": None,
    }
    headers = {
        "Authorization": f"Bearer {settings.INTERNAL_SERVICE_TOKEN}",
        "X-Tenant-ID": tenant_id,
    }
    try:
        with httpx.Client(timeout=3.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
            response = client.get(f"{settings.AGENT_RUNTIME_URL.rstrip('/')}/agents/status", headers=headers)
            response.raise_for_status()
            runtime_agents = response.json()
    except Exception as exc:
        diagnostics["agent_runtime_status"] = "unreachable"
        diagnostics["warning"] = str(exc)
        return [], diagnostics

    diagnostics["agent_runtime_status"] = "reachable"
    items = [_runtime_agent_item(agent) for agent in runtime_agents if isinstance(agent, dict)]
    diagnostics["runtime_agent_counts"] = _runtime_status_counts(items)
    diagnostics["runtime_unavailable_agent_ids"] = [
        item["id"] for item in items if item.get("runtime_status") != "active"
    ]
    if runtime_agents:
        diagnostics["feature_flags"] = runtime_agents[0].get("feature_flags") or {}
    return items, diagnostics


def _runtime_agent_item(agent: dict[str, Any]) -> dict[str, Any]:
    runtime_status = _normalize_runtime_status(agent)
    enabled = runtime_status == "active"
    return {
        "id": agent.get("agent_id"),
        "display_name": agent.get("name") or agent.get("agent_id"),
        "category": "llm_runtime_agent",
        "runtime_status": runtime_status,
        "status_reason": agent.get("status_reason") or _infer_status_reason(agent, runtime_status),
        "canonical_path": "backend/libs/sg_agent_runtime",
        "capabilities": agent.get("tools") or [],
        "enabled": enabled,
        "requires_approval": _runtime_agent_requires_approval(agent),
        "runtime_configured": bool(agent.get("runtime_configured", True)),
        "model_required": agent.get("model_required", True),
        "tool_count": agent.get("tool_count", 0),
        "missing_tools": agent.get("missing_tools") or [],
    }


def _runtime_ready_diagnostics(tenant_id: str) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {settings.INTERNAL_SERVICE_TOKEN}",
        "X-Tenant-ID": tenant_id,
    }
    try:
        with httpx.Client(timeout=3.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
            response = client.get(f"{settings.AGENT_RUNTIME_URL.rstrip('/')}/ready", headers=headers)
            try:
                payload = response.json()
            except Exception:
                payload = {}
    except Exception as exc:
        return {
            "status": "unreachable",
            "ready": False,
            "http_status_code": None,
            "warning": str(exc),
        }

    if not isinstance(payload, dict):
        payload = {}
    return {
        "status": "ready" if response.status_code == 200 else "not_ready",
        "ready": bool(payload.get("ready")),
        "http_status_code": response.status_code,
        "redis": payload.get("redis") or {},
        "active_agent_loops": payload.get("active_agent_loops") or [],
        "feature_flags": payload.get("feature_flags") or {},
        "warning": None if response.status_code == 200 else payload.get("status", "not_ready"),
    }


def _runtime_status_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"active": 0, "declared_only": 0, "disabled": 0, "unknown": 0}
    for item in items:
        status = str(item.get("runtime_status") or "unknown")
        if status not in counts:
            status = "unknown"
        counts[status] += 1
    return counts


def _normalize_runtime_status(agent: dict[str, Any]) -> str:
    status = str(agent.get("runtime_status") or "").strip().lower()
    if status == "available":
        return "active"
    if status in {"active", "declared_only", "disabled"}:
        return status
    if bool(agent.get("available")):
        return "active"
    flags = agent.get("feature_flags") or {}
    if agent.get("agent_id") == "compliance_agent" and flags.get("compliance_agent_enabled") is False:
        return "disabled"
    return "declared_only"


def _infer_status_reason(agent: dict[str, Any], runtime_status: str) -> str:
    if runtime_status == "active":
        return "runtime_loop_enabled"
    flags = agent.get("feature_flags") or {}
    if agent.get("agent_id") == "compliance_agent" and flags.get("compliance_agent_enabled") is False:
        return "feature_flag_disabled"
    if agent.get("missing_tools"):
        return "missing_or_disabled_tools"
    if runtime_status == "disabled":
        return "disabled"
    return "runtime_flow_not_enabled"


def _runtime_agent_requires_approval(agent: dict[str, Any]) -> bool:
    return agent.get("autonomy_level") == "approval_required" or agent.get("agent_id") == "compliance_agent"


def _endpoint_agent_inventory(tenant_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    versions_payload, diagnostics = _fetch_iam_agent_versions(tenant_id)
    if not versions_payload:
        diagnostics["endpoint_package_inventory_status"] = "fallback"
        return _fallback_endpoint_agent_inventory(), diagnostics

    endpoint_items = _endpoint_items_from_versions(versions_payload)
    if not endpoint_items:
        diagnostics["endpoint_package_inventory_status"] = "fallback"
        diagnostics["endpoint_package_warning"] = "IAM Agent returned no endpoint package versions"
        return _fallback_endpoint_agent_inventory(), diagnostics

    diagnostics["endpoint_package_inventory_status"] = "reachable"
    return endpoint_items, diagnostics


def _fetch_iam_agent_versions(tenant_id: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    diagnostics: dict[str, Any] = {
        "iam_agent_url": settings.IAM_AGENT_URL,
        "endpoint_package_inventory_status": "unknown",
        "endpoint_package_warning": None,
    }
    headers = {
        "Authorization": f"Bearer {settings.INTERNAL_SERVICE_TOKEN}",
        "X-Tenant-ID": tenant_id,
    }
    try:
        with httpx.Client(timeout=3.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
            response = client.get(f"{settings.IAM_AGENT_URL.rstrip('/')}/api/v1/agents/versions", headers=headers)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        diagnostics["endpoint_package_inventory_status"] = "unreachable"
        diagnostics["endpoint_package_warning"] = str(exc)
        return None, diagnostics

    if not isinstance(payload, dict):
        diagnostics["endpoint_package_inventory_status"] = "invalid"
        diagnostics["endpoint_package_warning"] = "IAM Agent returned a non-object versions payload"
        return None, diagnostics
    diagnostics["endpoint_package_inventory_status"] = "reachable"
    return payload, diagnostics


def _endpoint_items_from_versions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    versions = payload.get("versions") or []
    if not isinstance(versions, list):
        return []

    items: list[dict[str, Any]] = []
    for version in versions:
        if not isinstance(version, dict):
            continue
        agent_type = str(version.get("agent_type") or "").strip()
        if agent_type != "endpoint_protection":
            continue
        items.append(_sentinelguard_endpoint_item(version))
        if str(version.get("upstream_tool") or "").lower() == "wazuh":
            items.append(_wazuh_endpoint_item(version))
    return _dedupe_items(items)


def _sentinelguard_endpoint_item(version: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "sentinelguard_endpoint",
        "display_name": "SentinelGuard Endpoint Agent",
        "category": "endpoint_customer_agent",
        "runtime_status": "package_available",
        "canonical_path": "scripts/rebrand-agents",
        "capabilities": ["endpoint_telemetry", "heartbeat", "tenant_labeling"],
        "enabled": not bool(version.get("is_deprecated")),
        "requires_approval": False,
        "version": version.get("sentinelgrid_version"),
        "release_date": version.get("release_date"),
        "is_latest": bool(version.get("is_latest")),
        "is_deprecated": bool(version.get("is_deprecated")),
        "upstream_tool": version.get("upstream_tool"),
        "upstream_version": version.get("upstream_version"),
        "download_urls": version.get("download_urls") or {},
        "checksums": version.get("checksums") or {},
        "source": "iam_agent_versions_api",
    }


def _wazuh_endpoint_item(version: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "wazuh_endpoint",
        "display_name": "Wazuh Endpoint Package",
        "category": "endpoint_customer_agent",
        "runtime_status": "upstream_package",
        "canonical_path": "scripts/rebrand-agents/download",
        "capabilities": ["endpoint_events", "manager_labels"],
        "enabled": not bool(version.get("is_deprecated")),
        "requires_approval": False,
        "version": version.get("upstream_version"),
        "release_date": version.get("release_date"),
        "is_latest": bool(version.get("is_latest")),
        "is_deprecated": bool(version.get("is_deprecated")),
        "upstream_tool": version.get("upstream_tool"),
        "upstream_version": version.get("upstream_version"),
        "source": "iam_agent_versions_api",
    }


def _dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for item in items:
        item_id = item.get("id")
        if item_id:
            deduped[str(item_id)] = item
    return list(deduped.values())


def _agent_versions_response(payload: dict[str, Any]) -> dict[str, Any]:
    versions = payload.get("versions") or []
    latest = payload.get("latest_versions") or {}
    endpoint_latest = latest.get("endpoint_protection") if isinstance(latest, dict) else None
    latest_version = None
    if isinstance(endpoint_latest, dict):
        latest_version = endpoint_latest.get("upstream_version") or endpoint_latest.get("sentinelgrid_version")
    if latest_version is None and versions:
        first = versions[0]
        if isinstance(first, dict):
            latest_version = first.get("upstream_version") or first.get("sentinelgrid_version")

    return {
        "latest_version": latest_version or "4.8.0",
        "versions": versions,
        "latest_versions": latest,
        "source": "iam_agent_versions_api",
    }


def _fallback_agent_versions_response() -> dict[str, Any]:
    return {
        "latest_version": "4.8.0",
        "versions": [
            {"version": "4.8.0", "release_date": "2024-12-01", "is_latest": True},
            {"version": "4.7.2", "release_date": "2024-11-15", "is_latest": False},
        ],
        "source": "static_fallback",
    }


def _service_agent_inventory() -> list[dict[str, Any]]:
    return [
        {
            "id": "iam_agent",
            "display_name": "IAM Agent Service",
            "category": "service_agent",
            "runtime_status": "service",
            "canonical_path": "backend/agents/iam_agent",
            "capabilities": ["identity", "access_governance", "unified_chat_provider"],
            "enabled": True,
            "requires_approval": False,
        },
        {
            "id": "siem_agent",
            "display_name": "SIEM Agent Service",
            "category": "service_agent",
            "runtime_status": "service",
            "canonical_path": "backend/agents/siem_agent",
            "capabilities": ["detections", "log_search", "threat_events"],
            "enabled": True,
            "requires_approval": False,
        },
        {
            "id": "soar_agent",
            "display_name": "SOAR Agent Service",
            "category": "service_agent",
            "runtime_status": "service",
            "canonical_path": "backend/agents/soar_agent",
            "capabilities": ["incidents", "playbooks", "supervised_response"],
            "enabled": True,
            "requires_approval": True,
        },
        {
            "id": "mcp_server",
            "display_name": "MCP Server",
            "category": "service_agent",
            "runtime_status": "service",
            "canonical_path": "backend/agents/mcp_server",
            "capabilities": ["tool_catalog", "agent_tool_contracts"],
            "enabled": True,
            "requires_approval": False,
        },
    ]


def _fallback_endpoint_agent_inventory() -> list[dict[str, Any]]:
    return [
        {
            "id": "sentinelguard_endpoint",
            "display_name": "SentinelGuard Endpoint Agent",
            "category": "endpoint_customer_agent",
            "runtime_status": "package_available",
            "canonical_path": "scripts/rebrand-agents",
            "capabilities": ["endpoint_telemetry", "heartbeat", "tenant_labeling"],
            "enabled": True,
            "requires_approval": False,
            "version": "1.0.0",
            "upstream_tool": "wazuh",
            "upstream_version": "4.8.0",
            "source": "static_fallback",
        },
        {
            "id": "wazuh_endpoint",
            "display_name": "Wazuh Endpoint Package",
            "category": "endpoint_customer_agent",
            "runtime_status": "upstream_package",
            "canonical_path": "scripts/rebrand-agents/download",
            "capabilities": ["endpoint_events", "manager_labels"],
            "enabled": True,
            "requires_approval": False,
            "version": "4.8.0",
            "upstream_tool": "wazuh",
            "upstream_version": "4.8.0",
            "source": "static_fallback",
        },
    ]
