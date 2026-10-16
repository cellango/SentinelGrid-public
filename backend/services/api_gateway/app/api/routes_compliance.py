"""Compliance routes for entitlement reporting, reporting readiness, and workflow helpers."""

from collections import Counter
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, Security, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Any, Literal, Optional
import httpx
import sys
import os
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

from sg_core.db import get_tenant_session
from sg_core.security import get_current_tenant
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

router = APIRouter()
auth_scheme = HTTPBearer()


class EvidenceCollectRequest(BaseModel):
    """Request to collect compliance evidence for a mapped control."""
    control_id: str = Field(..., description="NIST control identifier such as IA-2 or AC-2")
    evidence_types: list[str] = Field(..., min_length=1, description="Evidence types to collect")
    tenant_id: Optional[str] = Field(default=None, description="Optional tenant override")


class FrameworkSelectionItem(BaseModel):
    framework_id: str
    status: str = "active"
    priority: Optional[int] = Field(default=None, ge=1)
    target_date: Optional[str] = None


class FrameworkSelectionUpdateRequest(BaseModel):
    tenant_id: Optional[str] = None
    selections: list[FrameworkSelectionItem] = Field(default_factory=list)


class EvidenceControlLinkRequest(BaseModel):
    control_id: str
    framework_id: Optional[str] = None
    evidence_requirement_id: Optional[str] = None
    package_id: Optional[str] = None
    link_type: str = "supports"
    rationale: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceCreateRequest(BaseModel):
    tenant_id: Optional[str] = None
    realm_name: str = "default"
    package_id: Optional[str] = None
    evidence_type: str
    title: str
    description: Optional[str] = None
    source_system: str
    source_resource_id: str
    collector: str
    collection_method: str
    collected_at: Optional[str] = None
    valid_from: str
    valid_until: str
    hash_sha256: str
    storage_uri: str
    summary: str
    sensitivity: str = "internal"
    review_status: str = "pending"
    created_by: Optional[str] = None
    control_links: list[EvidenceControlLinkRequest] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    integrity_metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceReviewRequest(BaseModel):
    tenant_id: Optional[str] = None
    review_status: str
    reviewer: Optional[str] = None
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    expires_at: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidencePackageCreateRequest(BaseModel):
    tenant_id: Optional[str] = None
    realm_name: str = "default"
    package_name: str
    framework_id: Optional[str] = None
    report_period_start: str
    report_period_end: str
    created_by: Optional[str] = None
    package_type: str = "audit_package"
    summary: Optional[str] = None
    description: Optional[str] = None
    sensitivity: str = "internal"
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_item_ids: list[str] = Field(default_factory=list)


class EvidencePackageExportRequest(BaseModel):
    tenant_id: Optional[str] = None
    export_format: Literal["pdf", "zip", "csv"]
    requested_by: Optional[str] = None
    include_sensitive: bool = False
    manifest: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceCollectionTaskCreateRequest(BaseModel):
    tenant_id: Optional[str] = None
    realm_name: str = "default"
    package_id: Optional[str] = None
    task_name: str
    task_type: str
    status: str = "pending"
    source_system: Optional[str] = None
    source_resource_id: Optional[str] = None
    collector: Optional[str] = None
    collection_method: Optional[str] = None
    requested_by: Optional[str] = None
    due_at: Optional[str] = None
    error_message: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None


class AgentRecommendationDecisionRequest(BaseModel):
    state: Literal["accepted", "rejected", "superseded"]
    decision_notes: Optional[str] = None
    superseded_by: Optional[str] = None


class ComplianceAdminSettingsUpdateRequest(BaseModel):
    multi_framework_selection: Optional[bool] = None
    durable_evidence_repository: Optional[bool] = None
    compliance_agent_workflows: Optional[bool] = None


def _runtime_labels() -> dict[str, str]:
    return {
        "dashboard_title": "Compliance Dashboard"
        if settings.COMPLIANCE_MULTI_FRAMEWORK_ENABLED
        else "SOC 2 Readiness Dashboard",
        "reports_title": "Compliance Reports"
        if settings.COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED
        else "Trust & SOC 2 Reports",
        "evidence_label": "Evidence items"
        if settings.COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED
        else "Report-ready signals",
    }


def _build_local_capabilities() -> dict[str, Any]:
    runtime_mode = (
        "multi_framework_compliance"
        if settings.COMPLIANCE_MULTI_FRAMEWORK_ENABLED
        else "soc2_readiness"
    )
    return {
        "runtime_mode": runtime_mode,
        "capabilities": {
            "soc2_readiness": True,
            "framework_starter_packs": True,
            "multi_framework_selection": settings.COMPLIANCE_MULTI_FRAMEWORK_ENABLED,
            "durable_evidence_repository": settings.COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED,
            "compliance_agent_workflows": settings.COMPLIANCE_AGENT_ENABLED,
        },
        "compatibility_endpoints": [
            "/api/v1/compliance/soc2/coverage",
            "/api/v1/compliance/dashboard",
            "/api/v1/compliance/evidence/collect",
        ],
        "stub_endpoints": [],
        "deprecated_endpoints": [
            {
                "path": "/api/v1/compliance/report",
                "replacement": "/api/v1/reports",
                "reason": "Legacy entitlement-style report shape is retained for compatibility; source data now comes from reporting_service.",
            },
        ],
        "truth_labels": _runtime_labels(),
        "admin_control_paths": {
            "readiness": "/api/v1/compliance/launch-readiness",
            "settings": "/api/v1/compliance/admin/settings",
        },
        "admin_controls": [
            {
                "key": "multi_framework_selection",
                "label": "Multi-framework selection",
                "env_var": "COMPLIANCE_MULTI_FRAMEWORK_ENABLED",
                "feature_flag_key": "compliance_multi_framework_enabled",
            },
            {
                "key": "durable_evidence_repository",
                "label": "Durable evidence repository",
                "env_var": "COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED",
                "feature_flag_key": "compliance_evidence_repository_enabled",
            },
            {
                "key": "compliance_agent_workflows",
                "label": "Compliance Agent workflows",
                "env_var": "COMPLIANCE_AGENT_ENABLED",
                "feature_flag_key": "compliance_agent_enabled",
            },
        ],
    }


def _build_proxy_headers(
    current_tenant_id: str,
    credentials: HTTPAuthorizationCredentials,
) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {credentials.credentials}",
        "X-Tenant-ID": current_tenant_id,
        "Content-Type": "application/json",
    }


def _enforce_same_tenant_override(
    requested_tenant_id: Optional[str],
    current_tenant_id: str,
) -> None:
    if requested_tenant_id and requested_tenant_id != current_tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Tenant ID mismatch. You can only access your own tenant's data.",
        )


async def _proxy_to_iam_compliance(
    method: str,
    path: str,
    current_tenant_id: str,
    credentials: HTTPAuthorizationCredentials,
    payload: Optional[dict[str, Any]] = None,
):
    url = f"{settings.IAM_AGENT_URL}/internal/iam/compliance{path}"
    headers = _build_proxy_headers(current_tenant_id, credentials)

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.request(method=method, url=url, headers=headers, json=payload)
        if response.status_code >= 400:
            detail = response.text
            try:
                parsed = response.json()
                detail = parsed.get("detail") or parsed
            except Exception:
                detail = response.text
            raise HTTPException(status_code=response.status_code, detail=detail)
        return response.json()


async def _proxy_to_compliance_service(
    path: str,
    method: str = "GET",
    headers: Optional[dict[str, str]] = None,
    payload: Optional[dict[str, Any]] = None,
    params: Optional[dict[str, Any]] = None,
):
    url = f"{settings.COMPLIANCE_SERVICE_URL}/api/v1/compliance{path}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.request(method=method, url=url, headers=headers, json=payload, params=params)
        if response.status_code >= 400:
            detail: Any = response.text
            try:
                parsed = response.json()
                detail = parsed.get("detail") or parsed
            except Exception:
                detail = response.text
            raise HTTPException(status_code=response.status_code, detail=detail)
        return response.json()


async def _proxy_to_reporting_service(
    path: str = "",
    headers: Optional[dict[str, str]] = None,
    params: Optional[dict[str, Any]] = None,
):
    normalized_path = path.lstrip("/")
    url = f"{settings.REPORTING_SERVICE_URL}/api/v1/reports/{normalized_path}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.request(method="GET", url=url, headers=headers, params=params)
        if response.status_code >= 400:
            detail: Any = response.text
            try:
                parsed = response.json()
                detail = parsed.get("detail") or parsed
            except Exception:
                detail = response.text
            raise HTTPException(status_code=response.status_code, detail=detail)
        return response.json()


async def _proxy_to_audit_service(
    path: str,
    headers: Optional[dict[str, str]] = None,
    params: Optional[dict[str, Any]] = None,
):
    url = f"{settings.AUDIT_SERVICE_URL}/api/v1/audit{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.request(method="GET", url=url, headers=headers, params=params)
        if response.status_code >= 400:
            detail: Any = response.text
            try:
                parsed = response.json()
                detail = parsed.get("detail") or parsed
            except Exception:
                detail = response.text
            raise HTTPException(status_code=response.status_code, detail=detail)
        return response.json()


async def _proxy_to_iam_agent(
    path: str,
    headers: Optional[dict[str, str]] = None,
    params: Optional[dict[str, Any]] = None,
):
    url = f"{settings.IAM_AGENT_URL}{path}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.request(method="GET", url=url, headers=headers, params=params)
        if response.status_code >= 400:
            detail: Any = response.text
            try:
                parsed = response.json()
                detail = parsed.get("detail") or parsed
            except Exception:
                detail = response.text
            raise HTTPException(status_code=response.status_code, detail=detail)
        return response.json()


def _status_value(item: dict[str, Any]) -> str:
    value = item.get("status") or "unknown"
    if isinstance(value, dict):
        value = value.get("value") or value.get("name") or "unknown"
    return str(value).strip().lower()


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _normalize_report_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("reports") or payload.get("results") or []
        return [item for item in items if isinstance(item, dict)]
    return []


def _build_legacy_report_response(
    tenant_id: str,
    reports_payload: Any,
) -> dict[str, Any]:
    reports = _normalize_report_items(reports_payload)
    status_counts = Counter(_status_value(report) for report in reports)
    report_type_counts = Counter(
        str(
            (report.get("metadata") or report.get("report_metadata") or {}).get("template_key")
            or (report.get("metadata") or report.get("report_metadata") or {}).get("report_type")
            or report.get("type")
            or "report"
        )
        for report in reports
    )

    report_timestamps = [
        parsed
        for parsed in (
            _parse_datetime(report.get("generated_at") or report.get("created_at") or report.get("updated_at"))
            for report in reports
        )
        if parsed is not None
    ]
    latest = max(report_timestamps, default=None)

    return {
        "tenant_id": tenant_id,
        "report_date": (latest or datetime.now(timezone.utc)).isoformat(),
        "total_entitlements": len(reports),
        "active_entitlements": status_counts.get("completed", 0),
        "revoked_entitlements": status_counts.get("failed", 0),
        "expired_entitlements": status_counts.get("expired", 0),
        "pending_review": status_counts.get("pending", 0) + status_counts.get("running", 0),
        "users_with_entitlements": 0,
        "entitlements_by_resource_type": dict(report_type_counts),
        "entitlements_by_action": dict(status_counts),
        "deprecated": True,
        "replacement_endpoint": "/api/v1/reports",
        "source": "reporting_service",
        "report_count": len(reports),
        "reports": [
            {
                "id": report.get("id"),
                "name": report.get("name"),
                "status": _status_value(report),
                "generated_at": report.get("generated_at") or report.get("created_at"),
            }
            for report in reports[:10]
        ],
    }


def _format_audit_result(log: dict[str, Any]) -> dict[str, Any]:
    timestamp = log.get("timestamp") or log.get("created_at") or log.get("updated_at")
    status = "success" if log.get("success", True) else "failed"
    return {
        "entitlement_id": log.get("resource_id") or log.get("id"),
        "resource_type": log.get("resource_type") or "compliance",
        "resource_id": log.get("resource_id") or log.get("id"),
        "action": log.get("action") or "compliance_event",
        "status": status,
        "updated_at": timestamp,
        "granted_at": timestamp,
        "actor_user_id": log.get("actor_user_id"),
        "actor_email": log.get("actor_email"),
        "resource_name": log.get("resource_name"),
        "metadata": log.get("metadata") or {},
    }


def _normalize_collection(payload: Any, *keys: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in keys:
            items = payload.get(key)
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
    return []


def _format_orphaned_entitlement(entitlement: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(entitlement.get("id")),
        "granted_to_id": str(entitlement.get("granted_to_id") or ""),
        "granted_to_type": str(entitlement.get("granted_to_type") or ""),
        "resource_type": str(entitlement.get("resource_type") or ""),
        "resource_id": str(entitlement.get("resource_id") or ""),
        "action": str(entitlement.get("action") or ""),
        "expired_at": entitlement.get("expires_at"),
        "status": entitlement.get("status"),
        "source": "iam_agent",
    }


@router.get("/capabilities")
async def get_compliance_capabilities():
    """Return Compliance module rollout flags and runtime truth labels."""
    url = f"{settings.COMPLIANCE_SERVICE_URL}/api/v1/compliance/capabilities"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError:
        return _build_local_capabilities()


@router.get("/launch-readiness")
async def get_compliance_launch_readiness(
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy Compliance module launch-readiness metadata from compliance_service."""
    headers = _build_proxy_headers(current_tenant_id, credentials)
    return await _proxy_to_compliance_service("/launch-readiness", headers=headers)


@router.get("/admin/settings")
async def get_compliance_admin_settings(
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy tenant Compliance launch controls from compliance_service."""
    headers = _build_proxy_headers(current_tenant_id, credentials)
    return await _proxy_to_compliance_service("/admin/settings", headers=headers)


@router.put("/admin/settings")
async def update_compliance_admin_settings(
    request: ComplianceAdminSettingsUpdateRequest,
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Update tenant Compliance launch controls through compliance_service."""
    headers = _build_proxy_headers(current_tenant_id, credentials)
    return await _proxy_to_compliance_service(
        "/admin/settings",
        method="PUT",
        headers=headers,
        payload=request.model_dump(exclude_none=True),
    )


@router.get("/framework-selections")
async def list_compliance_framework_selections(
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy tenant framework selections from compliance_service."""
    headers = _build_proxy_headers(current_tenant_id, credentials)
    return await _proxy_to_compliance_service("/framework-selections", headers=headers)


@router.put("/framework-selections")
async def replace_compliance_framework_selections(
    request: FrameworkSelectionUpdateRequest,
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Replace tenant framework selections through compliance_service."""
    _enforce_same_tenant_override(request.tenant_id, current_tenant_id)
    payload = request.model_dump()
    payload["tenant_id"] = current_tenant_id
    headers = _build_proxy_headers(current_tenant_id, credentials)
    return await _proxy_to_compliance_service(
        "/framework-selections",
        method="PUT",
        headers=headers,
        payload=payload,
    )


@router.get("/frameworks")
async def list_compliance_frameworks():
    """Proxy compliance framework catalog metadata from compliance_service."""
    return await _proxy_to_compliance_service("/frameworks")


@router.get("/frameworks/{framework_id}/controls")
async def list_compliance_framework_controls(framework_id: str):
    """Proxy compliance controls for a framework catalog."""
    return await _proxy_to_compliance_service(f"/frameworks/{framework_id}/controls")


@router.get("/frameworks/{framework_id}/coverage")
async def get_compliance_framework_coverage(
    framework_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy generalized coverage for a single compliance framework."""
    headers = _build_proxy_headers(current_tenant_id, credentials)
    return await _proxy_to_compliance_service(
        f"/frameworks/{framework_id}/coverage",
        headers=headers,
        params={"limit": limit, "offset": offset},
    )


@router.get("/frameworks/{framework_id}")
async def get_compliance_framework(framework_id: str):
    """Proxy compliance framework catalog detail from compliance_service."""
    return await _proxy_to_compliance_service(f"/frameworks/{framework_id}")


@router.get("/coverage")
async def get_compliance_coverage(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy generalized coverage for selected compliance frameworks."""
    headers = _build_proxy_headers(current_tenant_id, credentials)
    return await _proxy_to_compliance_service(
        "/coverage",
        headers=headers,
        params={"limit": limit, "offset": offset},
    )


@router.get("/controls/{control_id}/status")
async def get_compliance_control_status(
    control_id: str,
    framework_id: Optional[str] = Query(None),
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy generalized status for a compliance control."""
    headers = _build_proxy_headers(current_tenant_id, credentials)
    params = {"framework_id": framework_id} if framework_id else {}
    return await _proxy_to_compliance_service(
        f"/controls/{control_id}/status",
        headers=headers,
        params=params,
    )


@router.get("/report")
async def get_compliance_report(
    tenant_id: str = Query(..., description="Tenant ID"),
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Deprecated compatibility report backed by reporting_service."""
    _enforce_same_tenant_override(tenant_id, current_tenant_id)
    headers = _build_proxy_headers(current_tenant_id, credentials)
    payload = await _proxy_to_reporting_service(
        headers=headers,
        params={"limit": 200, "offset": 0},
    )
    return _build_legacy_report_response(current_tenant_id, payload)


@router.get("/audit-trail")
async def get_audit_trail(
    tenant_id: str = Query(..., description="Tenant ID"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    realm_name: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    x_realm: Optional[str] = Header(None, alias="X-Realm"),
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Get compliance audit trail from audit_service."""
    _enforce_same_tenant_override(tenant_id, current_tenant_id)
    headers = _build_proxy_headers(current_tenant_id, credentials)
    params = {
        "tenant_id": current_tenant_id,
        "realm_name": realm_name or x_realm or "sentinelgrid",
        "start_date": start_date,
        "end_date": end_date,
        "action_category": "compliance",
        "limit": limit,
        "offset": offset,
    }
    payload = await _proxy_to_audit_service(
        "/logs",
        headers=headers,
        params={key: value for key, value in params.items() if value is not None},
    )
    logs = _normalize_collection(payload, "logs", "items", "results")
    return {
        "count": int(payload.get("count") or len(logs)) if isinstance(payload, dict) else len(logs),
        "limit": limit,
        "offset": offset,
        "results": [_format_audit_result(log) for log in logs],
        "source": "audit_service",
        "filters": {"action_category": "compliance"},
    }


@router.get("/orphaned-entitlements")
async def get_orphaned_entitlements(
    tenant_id: str = Query(..., description="Tenant ID"),
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Get orphaned entitlements from IAM/entitlement data."""
    _enforce_same_tenant_override(tenant_id, current_tenant_id)
    headers = _build_proxy_headers(current_tenant_id, credentials)
    entitlements_payload = await _proxy_to_iam_agent(
        "/api/v1/entitlements",
        headers=headers,
        params={"tenant_id": current_tenant_id, "limit": 1000, "offset": 0},
    )
    users_payload = await _proxy_to_iam_agent(
        "/api/iam-portal/users",
        headers=headers,
    )
    entitlements = _normalize_collection(entitlements_payload, "items", "entitlements", "results")
    users = _normalize_collection(users_payload, "items", "users", "results")
    active_user_ids = {
        str(user.get("user_id") or user.get("id"))
        for user in users
        if user.get("enabled", True) and (user.get("user_id") or user.get("id"))
    }
    active_statuses = {"active", "granted", "approved"}
    orphaned = [
        entitlement
        for entitlement in entitlements
        if str(entitlement.get("granted_to_type") or "").lower() == "user"
        and str(entitlement.get("status") or "active").lower() in active_statuses
        and str(entitlement.get("granted_to_id") or "") not in active_user_ids
    ]
    return {
        "tenant_id": current_tenant_id,
        "orphaned_count": len(orphaned),
        "entitlements": [_format_orphaned_entitlement(entitlement) for entitlement in orphaned],
        "source": "iam_agent",
        "evaluated_entitlements": len(entitlements),
        "active_user_count": len(active_user_ids),
    }


@router.get("/soc2/coverage")
async def get_soc2_coverage(
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy SOC 2 coverage from compliance_service."""
    url = f"{settings.COMPLIANCE_SERVICE_URL}/api/v1/compliance/soc2/coverage"
    headers = _build_proxy_headers(current_tenant_id, credentials)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()


@router.get("/dashboard")
async def get_compliance_dashboard(
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy compliance dashboard summary from compliance_service."""
    url = f"{settings.COMPLIANCE_SERVICE_URL}/api/v1/compliance/dashboard"
    headers = _build_proxy_headers(current_tenant_id, credentials)
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()


@router.get("/agent/recommendations")
async def list_compliance_agent_recommendations(
    state: Optional[str] = Query(None),
    trigger_type: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    framework_id: Optional[str] = Query(None),
    control_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy reviewable Compliance Agent recommendations from compliance_service."""
    headers = _build_proxy_headers(current_tenant_id, credentials)
    params = {
        "state": state,
        "trigger_type": trigger_type,
        "source_type": source_type,
        "framework_id": framework_id,
        "control_id": control_id,
        "limit": limit,
        "offset": offset,
    }
    return await _proxy_to_compliance_service(
        "/agent/recommendations",
        headers=headers,
        params={key: value for key, value in params.items() if value is not None},
    )


@router.post("/agent/recommendations/{recommendation_id}/decision")
async def decide_compliance_agent_recommendation(
    recommendation_id: str,
    request: AgentRecommendationDecisionRequest,
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy supervised Compliance Agent recommendation decisions to compliance_service."""
    headers = _build_proxy_headers(current_tenant_id, credentials)
    return await _proxy_to_compliance_service(
        f"/agent/recommendations/{recommendation_id}/decision",
        method="POST",
        headers=headers,
        payload=request.model_dump(exclude_none=True),
    )


@router.get("/evidence")
async def list_compliance_evidence(
    tenant_id: Optional[str] = Query(None),
    framework_id: Optional[str] = Query(None),
    control_id: Optional[str] = Query(None),
    source_system: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    package_id: Optional[str] = Query(None),
    expires_before: Optional[str] = Query(None),
    expires_after: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy durable evidence inventory reads from compliance_service."""
    _enforce_same_tenant_override(tenant_id, current_tenant_id)
    headers = _build_proxy_headers(current_tenant_id, credentials)
    params = {
        "tenant_id": current_tenant_id,
        "framework_id": framework_id,
        "control_id": control_id,
        "source_system": source_system,
        "review_status": review_status,
        "package_id": package_id,
        "expires_before": expires_before,
        "expires_after": expires_after,
        "limit": limit,
        "offset": offset,
    }
    return await _proxy_to_compliance_service(
        "/evidence",
        headers=headers,
        params={key: value for key, value in params.items() if value is not None},
    )


@router.post("/evidence")
async def create_compliance_evidence(
    request: EvidenceCreateRequest,
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy durable evidence item creation to compliance_service."""
    _enforce_same_tenant_override(request.tenant_id, current_tenant_id)
    payload = request.model_dump()
    payload["tenant_id"] = current_tenant_id
    headers = _build_proxy_headers(current_tenant_id, credentials)
    return await _proxy_to_compliance_service(
        "/evidence",
        method="POST",
        headers=headers,
        payload=payload,
    )


@router.get("/evidence/packages")
async def list_compliance_evidence_packages(
    tenant_id: Optional[str] = Query(None),
    framework_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy durable evidence package list reads from compliance_service."""
    _enforce_same_tenant_override(tenant_id, current_tenant_id)
    headers = _build_proxy_headers(current_tenant_id, credentials)
    params = {
        "tenant_id": current_tenant_id,
        "framework_id": framework_id,
        "status": status,
        "review_status": review_status,
        "limit": limit,
        "offset": offset,
    }
    return await _proxy_to_compliance_service(
        "/evidence/packages",
        headers=headers,
        params={key: value for key, value in params.items() if value is not None},
    )


@router.post("/evidence/packages")
async def create_compliance_evidence_package(
    request: EvidencePackageCreateRequest,
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy durable evidence package creation to compliance_service."""
    _enforce_same_tenant_override(request.tenant_id, current_tenant_id)
    payload = request.model_dump()
    payload["tenant_id"] = current_tenant_id
    headers = _build_proxy_headers(current_tenant_id, credentials)
    return await _proxy_to_compliance_service(
        "/evidence/packages",
        method="POST",
        headers=headers,
        payload=payload,
    )


@router.get("/evidence/tasks")
async def list_compliance_evidence_collection_tasks(
    tenant_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    source_system: Optional[str] = Query(None),
    package_id: Optional[str] = Query(None),
    due_before: Optional[str] = Query(None),
    due_after: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy durable evidence collection task list reads from compliance_service."""
    _enforce_same_tenant_override(tenant_id, current_tenant_id)
    headers = _build_proxy_headers(current_tenant_id, credentials)
    params = {
        "tenant_id": current_tenant_id,
        "status": status,
        "task_type": task_type,
        "source_system": source_system,
        "package_id": package_id,
        "due_before": due_before,
        "due_after": due_after,
        "limit": limit,
        "offset": offset,
    }
    return await _proxy_to_compliance_service(
        "/evidence/tasks",
        headers=headers,
        params={key: value for key, value in params.items() if value is not None},
    )


@router.post("/evidence/tasks")
async def create_compliance_evidence_collection_task(
    request: EvidenceCollectionTaskCreateRequest,
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy durable evidence collection task creation to compliance_service."""
    _enforce_same_tenant_override(request.tenant_id, current_tenant_id)
    payload = request.model_dump()
    payload["tenant_id"] = current_tenant_id
    headers = _build_proxy_headers(current_tenant_id, credentials)
    return await _proxy_to_compliance_service(
        "/evidence/tasks",
        method="POST",
        headers=headers,
        payload=payload,
    )


@router.get("/evidence/packages/{package_id}")
async def get_compliance_evidence_package(
    package_id: str,
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy durable evidence package detail from compliance_service."""
    headers = _build_proxy_headers(current_tenant_id, credentials)
    return await _proxy_to_compliance_service(
        f"/evidence/packages/{package_id}",
        headers=headers,
    )


@router.post("/evidence/packages/{package_id}/export")
async def export_compliance_evidence_package(
    package_id: str,
    request: EvidencePackageExportRequest,
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy durable evidence package export requests to compliance_service."""
    _enforce_same_tenant_override(request.tenant_id, current_tenant_id)
    payload = request.model_dump()
    payload["tenant_id"] = current_tenant_id
    headers = _build_proxy_headers(current_tenant_id, credentials)
    return await _proxy_to_compliance_service(
        f"/evidence/packages/{package_id}/export",
        method="POST",
        headers=headers,
        payload=payload,
    )


@router.get("/evidence/{evidence_id}")
async def get_compliance_evidence(
    evidence_id: str,
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy durable evidence item detail from compliance_service."""
    headers = _build_proxy_headers(current_tenant_id, credentials)
    return await _proxy_to_compliance_service(
        f"/evidence/{evidence_id}",
        headers=headers,
    )


@router.post("/evidence/{evidence_id}/review")
async def review_compliance_evidence(
    evidence_id: str,
    request: EvidenceReviewRequest,
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy durable evidence review decisions to compliance_service."""
    _enforce_same_tenant_override(request.tenant_id, current_tenant_id)
    payload = request.model_dump()
    payload["tenant_id"] = current_tenant_id
    headers = _build_proxy_headers(current_tenant_id, credentials)
    return await _proxy_to_compliance_service(
        f"/evidence/{evidence_id}/review",
        method="POST",
        headers=headers,
        payload=payload,
    )


@router.post("/evidence/collect")
async def collect_compliance_evidence(
    request: EvidenceCollectRequest,
    current_tenant_id: str = Depends(get_current_tenant),
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
):
    """Proxy evidence collection to the IAM agent compliance service."""
    _enforce_same_tenant_override(request.tenant_id, current_tenant_id)
    payload = request.model_dump()
    payload["tenant_id"] = current_tenant_id
    return await _proxy_to_iam_compliance(
        method="POST",
        path="/evidence/collect",
        current_tenant_id=current_tenant_id,
        credentials=credentials,
        payload=payload,
    )
