"""Durable compliance evidence repository endpoints."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from sg_core.security import get_current_payload

from app.core.database import get_current_tenant, get_tenant_session
from app.api.agent_workflow import get_compliance_agent_workflow_service
from app.schemas.evidence import (
    EvidenceCollectionTaskCreateRequest,
    EvidenceCreateRequest,
    EvidenceExportFinalizeRequest,
    EvidenceHashRequest,
    EvidenceHashResponse,
    EvidenceIntegrityVerificationRequest,
    EvidencePackageCreateRequest,
    EvidencePackageExportRequest,
    EvidenceRecollectionTaskRequest,
    EvidenceRetentionPolicyUpsertRequest,
    EvidenceRetireRequest,
    EvidenceReviewRequest,
)
from app.services.audit_client import AuditClient
from app.services.evidence_repository import (
    EvidenceNotFoundError,
    EvidenceRepositoryError,
    evidence_repository,
)
from app.services.observability import (
    record_evidence_collection,
    record_evidence_collection_task,
    record_stale_evidence_count,
)
from sg_agent_runtime.compliance_workflow import (
    build_evidence_collected_recommendation,
    build_evidence_expiration_recommendation,
)

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])

logger = logging.getLogger(__name__)


COLLECT_ROLES = {
    "admin",
    "tenant_admin",
    "compliance_manager",
    "compliance_officer",
    "evidence_collector",
    "evidence_reviewer",
    "soc_manager",
}
REVIEW_ROLES = {
    "admin",
    "tenant_admin",
    "compliance_manager",
    "compliance_officer",
    "evidence_reviewer",
    "soc_manager",
}
EXPORT_ROLES = {
    "admin",
    "tenant_admin",
    "compliance_manager",
    "compliance_officer",
    "evidence_reviewer",
    "report_exporter",
}
RETENTION_ROLES = {
    "admin",
    "tenant_admin",
    "compliance_manager",
    "compliance_officer",
}
EVIDENCE_EXPIRING_WINDOW_DAYS = 30


def _normalize_role(role: str) -> str:
    return role.strip().lower().replace("-", "_").replace(" ", "_")


def _roles_from_payload(token_payload: dict[str, Any]) -> set[str]:
    roles = token_payload.get("roles") or token_payload.get("realm_roles") or []
    return {_normalize_role(str(role)) for role in roles if str(role).strip()}


def _require_role(token_payload: dict[str, Any], allowed_roles: set[str]) -> None:
    roles = _roles_from_payload(token_payload)
    if not roles.intersection(allowed_roles):
        raise HTTPException(status_code=403, detail="Required compliance evidence role not found")


def _actor_id(token_payload: dict[str, Any], actor_header: str | None = None) -> str:
    return (
        actor_header
        or token_payload.get("user_id")
        or token_payload.get("sub")
        or token_payload.get("preferred_username")
        or "authenticated_user"
    )


def _resolve_tenant_id(
    current_tenant: str,
    override_tenant: Optional[str],
    tenant_id: Optional[str],
) -> str:
    if override_tenant and override_tenant != current_tenant:
        raise HTTPException(status_code=403, detail="Cross-tenant access denied")
    if tenant_id and tenant_id != current_tenant:
        raise HTTPException(status_code=403, detail="Cross-tenant access denied")
    return current_tenant


def _request_payload(model) -> dict[str, Any]:
    return model.model_dump(mode="python")


async def _audit_evidence_event(
    *,
    action: str,
    tenant_id: str,
    actor_user_id: str,
    resource_type: str,
    resource_id: str,
    resource_name: str | None = None,
    success: bool = True,
    metadata: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "tenant_id": tenant_id,
        "action": action,
        "action_category": "compliance",
        "actor_user_id": actor_user_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "success": success,
        "metadata": metadata or {},
    }
    if resource_name:
        payload["resource_name"] = resource_name
    if error_message:
        payload["error_message"] = error_message

    try:
        await AuditClient().log_event(payload)
    except Exception as exc:  # pragma: no cover - AuditClient already guards network failures.
        logger.warning("Failed to audit evidence event %s for %s: %s", action, resource_id, exc)


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


async def _trigger_evidence_lifecycle_recommendations(
    *,
    workflow_service,
    db: Session,
    tenant_id: str,
    evidence: dict[str, Any],
    actor_id: str | None,
    authorization: str | None,
    include_collected: bool = True,
) -> None:
    if include_collected:
        recommendation = build_evidence_collected_recommendation(evidence)
        try:
            await workflow_service.create_recommendation_and_task(
                db,
                tenant_id=tenant_id,
                created_by=actor_id,
                authorization=authorization,
                metadata={"evidence": evidence},
                **recommendation,
            )
        except Exception as exc:  # pragma: no cover - recommendation triggers are side effects.
            logger.warning(
                "Failed to trigger Compliance Agent evidence collection recommendation for tenant %s evidence %s: %s",
                tenant_id,
                evidence.get("id") or evidence.get("evidence_item_id"),
                exc,
            )

    valid_until = _parse_datetime(evidence.get("valid_until"))
    if not valid_until:
        return

    now = datetime.now(timezone.utc)
    if valid_until <= now:
        recommendation = build_evidence_expiration_recommendation(evidence, expired=True)
    elif valid_until <= now + timedelta(days=EVIDENCE_EXPIRING_WINDOW_DAYS):
        recommendation = build_evidence_expiration_recommendation(evidence, expired=False)
    else:
        return

    try:
        await workflow_service.create_recommendation_and_task(
            db,
            tenant_id=tenant_id,
            created_by=actor_id,
            authorization=authorization,
            metadata={"evidence": evidence},
            **recommendation,
        )
    except Exception as exc:  # pragma: no cover - recommendation triggers are side effects.
        logger.warning(
            "Failed to trigger Compliance Agent evidence expiration recommendation for tenant %s evidence %s: %s",
            tenant_id,
            evidence.get("id") or evidence.get("evidence_item_id"),
            exc,
        )


@router.get("/evidence")
def list_evidence(
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    tenant_id: Optional[str] = Query(None),
    framework_id: Optional[str] = Query(None),
    control_id: Optional[str] = Query(None),
    source_system: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    package_id: Optional[str] = Query(None),
    expires_before: Optional[datetime] = Query(None),
    expires_after: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List durable evidence items for the authenticated tenant."""
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, tenant_id)
    payload = evidence_repository.list_evidence(
        db,
        resolved_tenant_id,
        {
            "framework_id": framework_id,
            "control_id": control_id,
            "source_system": source_system,
            "review_status": review_status,
            "package_id": package_id,
            "expires_before": expires_before,
            "expires_after": expires_after,
        },
        limit=limit,
        offset=offset,
    )
    try:
        stale_count = evidence_repository.count_stale_evidence(db, resolved_tenant_id)
        record_stale_evidence_count(tenant_id=resolved_tenant_id, count=stale_count)
        payload["stale_evidence_count"] = stale_count
    except Exception as exc:  # pragma: no cover - metrics must not break reads.
        logger.warning("Failed to record stale evidence metric for tenant %s: %s", resolved_tenant_id, exc)
    return payload


@router.post("/evidence")
async def create_evidence(
    request: EvidenceCreateRequest,
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    actor_header: Optional[str] = Header(None, alias="X-User-ID"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    workflow_service=Depends(get_compliance_agent_workflow_service),
):
    """Create a durable evidence item and optional control links."""
    _require_role(token_payload, COLLECT_ROLES)
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, request.tenant_id)
    try:
        evidence = evidence_repository.create_evidence_item(
            db,
            resolved_tenant_id,
            _request_payload(request),
            actor_id=_actor_id(token_payload, actor_header),
        )
        record_evidence_collection(
            outcome="success",
            source_system=request.source_system,
            collection_method=request.collection_method,
        )
        await _trigger_evidence_lifecycle_recommendations(
            workflow_service=workflow_service,
            db=db,
            tenant_id=resolved_tenant_id,
            evidence=evidence,
            actor_id=_actor_id(token_payload, actor_header),
            authorization=authorization,
            include_collected=True,
        )
        return evidence
    except EvidenceRepositoryError as exc:
        record_evidence_collection(
            outcome="failure",
            source_system=request.source_system,
            collection_method=request.collection_method,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/evidence/hash", response_model=EvidenceHashResponse)
def calculate_evidence_hash(
    request: EvidenceHashRequest,
    token_payload: dict[str, Any] = Depends(get_current_payload),
):
    """Calculate a SHA-256 hash for evidence content before repository submission."""
    _require_role(token_payload, COLLECT_ROLES)
    try:
        return EvidenceHashResponse.from_request(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {request.encoding} content") from exc


@router.get("/evidence/packages")
def list_evidence_packages(
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    tenant_id: Optional[str] = Query(None),
    framework_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List tenant-scoped evidence packages."""
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, tenant_id)
    return evidence_repository.list_packages(
        db,
        resolved_tenant_id,
        {
            "framework_id": framework_id,
            "status": status,
            "review_status": review_status,
        },
        limit=limit,
        offset=offset,
    )


@router.post("/evidence/packages")
def create_evidence_package(
    request: EvidencePackageCreateRequest,
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    actor_header: Optional[str] = Header(None, alias="X-User-ID"),
):
    """Create a tenant-scoped evidence package."""
    _require_role(token_payload, COLLECT_ROLES)
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, request.tenant_id)
    try:
        return evidence_repository.create_package(
            db,
            resolved_tenant_id,
            _request_payload(request),
            actor_id=_actor_id(token_payload, actor_header),
        )
    except EvidenceRepositoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/evidence/tasks")
def list_evidence_collection_tasks(
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    tenant_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    source_system: Optional[str] = Query(None),
    package_id: Optional[str] = Query(None),
    due_before: Optional[datetime] = Query(None),
    due_after: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List durable evidence collection tasks."""
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, tenant_id)
    return evidence_repository.list_collection_tasks(
        db,
        resolved_tenant_id,
        {
            "status": status,
            "task_type": task_type,
            "source_system": source_system,
            "package_id": package_id,
            "due_before": due_before,
            "due_after": due_after,
        },
        limit=limit,
        offset=offset,
    )


@router.post("/evidence/tasks")
def create_evidence_collection_task(
    request: EvidenceCollectionTaskCreateRequest,
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    actor_header: Optional[str] = Header(None, alias="X-User-ID"),
):
    """Create a durable evidence collection task for unavailable or manual evidence."""
    _require_role(token_payload, COLLECT_ROLES)
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, request.tenant_id)
    try:
        task = evidence_repository.create_collection_task(
            db,
            resolved_tenant_id,
            _request_payload(request),
            actor_id=_actor_id(token_payload, actor_header),
        )
        record_evidence_collection_task(status=task.get("status") or request.status, task_type=request.task_type)
        return task
    except EvidenceRepositoryError as exc:
        record_evidence_collection_task(status="failed", task_type=request.task_type)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/evidence/retention-policies")
def list_evidence_retention_policies(
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    tenant_id: Optional[str] = Query(None),
    framework_id: Optional[str] = Query(None),
    subject_type: Optional[str] = Query(None),
):
    """List tenant-scoped evidence retention policies."""
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, tenant_id)
    return evidence_repository.list_retention_policies(
        db,
        resolved_tenant_id,
        {"framework_id": framework_id, "subject_type": subject_type},
    )


@router.put("/evidence/retention-policies")
async def upsert_evidence_retention_policy(
    request: EvidenceRetentionPolicyUpsertRequest,
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    actor_header: Optional[str] = Header(None, alias="X-User-ID"),
):
    """Create or update a tenant/framework evidence retention policy."""
    _require_role(token_payload, RETENTION_ROLES)
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, request.tenant_id)
    policy = evidence_repository.upsert_retention_policy(
        db,
        resolved_tenant_id,
        _request_payload(request),
        actor_id=_actor_id(token_payload, actor_header),
    )
    await _audit_evidence_event(
        action="evidence_retention_policy_upserted",
        tenant_id=resolved_tenant_id,
        actor_user_id=_actor_id(token_payload, actor_header),
        resource_type="evidence_retention_policy",
        resource_id=policy["id"],
        resource_name=policy.get("policy_name"),
        metadata={
            "framework_id": policy.get("framework_id"),
            "subject_type": policy.get("subject_type"),
            "retention_days": policy.get("retention_days"),
            "legal_hold": policy.get("legal_hold"),
        },
    )
    return policy


@router.get("/evidence/packages/{package_id}")
async def get_evidence_package(
    package_id: str,
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    actor_header: Optional[str] = Header(None, alias="X-User-ID"),
):
    """Get a tenant-scoped evidence package with items and export history."""
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, None)
    try:
        package = evidence_repository.get_package(db, resolved_tenant_id, package_id)
        await _audit_evidence_event(
            action="evidence_package_read",
            tenant_id=resolved_tenant_id,
            actor_user_id=_actor_id(token_payload, actor_header),
            resource_type="evidence_package",
            resource_id=package_id,
            resource_name=package.get("package_name"),
            metadata={"evidence_item_count": package.get("evidence_item_count", 0)},
        )
        return package
    except EvidenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/evidence/packages/{package_id}/export")
async def export_evidence_package(
    package_id: str,
    request: EvidencePackageExportRequest,
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    actor_header: Optional[str] = Header(None, alias="X-User-ID"),
):
    """Request an evidence package export record."""
    _require_role(token_payload, EXPORT_ROLES)
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, request.tenant_id)
    try:
        export = evidence_repository.create_export(
            db,
            resolved_tenant_id,
            package_id,
            _request_payload(request),
            actor_id=_actor_id(token_payload, actor_header),
        )
        await _audit_evidence_event(
            action="evidence_export_requested",
            tenant_id=resolved_tenant_id,
            actor_user_id=_actor_id(token_payload, actor_header),
            resource_type="evidence_export",
            resource_id=export["id"],
            metadata={
                "package_id": package_id,
                "export_format": export.get("export_format"),
                "include_sensitive": export.get("include_sensitive"),
                "manifest_hash_sha256": (export.get("manifest") or {}).get("manifest_hash_sha256"),
            },
        )
        return export
    except EvidenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EvidenceRepositoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/evidence/packages/{package_id}/exports/{export_id}")
async def finalize_evidence_package_export(
    package_id: str,
    export_id: str,
    request: EvidenceExportFinalizeRequest,
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    actor_header: Optional[str] = Header(None, alias="X-User-ID"),
):
    """Finalize an evidence export artifact; completed exports become immutable."""
    _require_role(token_payload, EXPORT_ROLES)
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, request.tenant_id)
    try:
        export = evidence_repository.complete_export(
            db,
            resolved_tenant_id,
            package_id,
            export_id,
            _request_payload(request),
            actor_id=_actor_id(token_payload, actor_header),
        )
        await _audit_evidence_event(
            action="evidence_export_finalized",
            tenant_id=resolved_tenant_id,
            actor_user_id=_actor_id(token_payload, actor_header),
            resource_type="evidence_export",
            resource_id=export_id,
            metadata={
                "package_id": package_id,
                "status": export.get("status"),
                "hash_sha256": export.get("hash_sha256"),
                "immutable_after": export.get("immutable_after"),
            },
        )
        return export
    except EvidenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EvidenceRepositoryError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/evidence/{evidence_id}")
async def get_evidence(
    evidence_id: str,
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    actor_header: Optional[str] = Header(None, alias="X-User-ID"),
):
    """Get a durable evidence item with links and review history."""
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, None)
    try:
        evidence = evidence_repository.get_evidence_item(db, resolved_tenant_id, evidence_id)
        await _audit_evidence_event(
            action="evidence_read",
            tenant_id=resolved_tenant_id,
            actor_user_id=_actor_id(token_payload, actor_header),
            resource_type="evidence_item",
            resource_id=evidence_id,
            resource_name=evidence.get("title"),
            metadata={
                "review_status": evidence.get("review_status"),
                "valid_until": evidence.get("valid_until"),
            },
        )
        return evidence
    except EvidenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/evidence/{evidence_id}/verify")
async def verify_evidence_integrity(
    evidence_id: str,
    request: EvidenceIntegrityVerificationRequest,
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    actor_header: Optional[str] = Header(None, alias="X-User-ID"),
):
    """Verify a stored evidence item against an observed SHA-256 hash."""
    _require_role(token_payload, REVIEW_ROLES)
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, request.tenant_id)
    try:
        verification = evidence_repository.verify_evidence_item(
            db,
            resolved_tenant_id,
            evidence_id,
            _request_payload(request),
            actor_id=_actor_id(token_payload, actor_header),
        )
        await _audit_evidence_event(
            action="evidence_integrity_verified",
            tenant_id=resolved_tenant_id,
            actor_user_id=_actor_id(token_payload, actor_header),
            resource_type="evidence_item",
            resource_id=evidence_id,
            resource_name=(verification.get("evidence") or {}).get("title"),
            metadata={
                "verification_status": (verification.get("verification") or {}).get("verification_status"),
                "verification_method": (verification.get("verification") or {}).get("verification_method"),
            },
        )
        return verification
    except EvidenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/evidence/{evidence_id}/recollection-task")
async def schedule_evidence_recollection_task(
    evidence_id: str,
    request: EvidenceRecollectionTaskRequest,
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    actor_header: Optional[str] = Header(None, alias="X-User-ID"),
):
    """Create a tenant-scoped recollection task for expired or stale evidence."""
    _require_role(token_payload, COLLECT_ROLES)
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, request.tenant_id)
    try:
        task = evidence_repository.schedule_recollection_task(
            db,
            resolved_tenant_id,
            evidence_id,
            _request_payload(request),
            actor_id=_actor_id(token_payload, actor_header),
        )
        record_evidence_collection_task(status=task.get("status") or request.task_status, task_type="evidence_recollection")
        await _audit_evidence_event(
            action="evidence_recollection_scheduled",
            tenant_id=resolved_tenant_id,
            actor_user_id=_actor_id(token_payload, actor_header),
            resource_type="evidence_collection_task",
            resource_id=task["id"],
            resource_name=task.get("task_name"),
            metadata={"source_evidence_id": evidence_id, "reason": request.reason},
        )
        return task
    except EvidenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except EvidenceRepositoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/evidence/{evidence_id}/retire")
async def retire_evidence(
    evidence_id: str,
    request: EvidenceRetireRequest,
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    actor_header: Optional[str] = Header(None, alias="X-User-ID"),
):
    """Retire evidence so it cannot be treated as active audit support."""
    _require_role(token_payload, REVIEW_ROLES)
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, request.tenant_id)
    try:
        evidence = evidence_repository.retire_evidence_item(
            db,
            resolved_tenant_id,
            evidence_id,
            actor_id=_actor_id(token_payload, actor_header),
            metadata={"reason": request.reason, "review_notes": request.review_notes, **request.metadata},
        )
        await _audit_evidence_event(
            action="evidence_retired",
            tenant_id=resolved_tenant_id,
            actor_user_id=_actor_id(token_payload, actor_header),
            resource_type="evidence_item",
            resource_id=evidence_id,
            resource_name=evidence.get("title"),
            metadata={"review_status": evidence.get("review_status")},
        )
        return evidence
    except EvidenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/evidence/{evidence_id}")
async def delete_evidence(
    evidence_id: str,
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    actor_header: Optional[str] = Header(None, alias="X-User-ID"),
):
    """Soft-delete a tenant-scoped evidence item."""
    _require_role(token_payload, REVIEW_ROLES)
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, None)
    try:
        evidence = evidence_repository.delete_evidence_item(
            db,
            resolved_tenant_id,
            evidence_id,
            actor_id=_actor_id(token_payload, actor_header),
        )
        await _audit_evidence_event(
            action="evidence_deleted",
            tenant_id=resolved_tenant_id,
            actor_user_id=_actor_id(token_payload, actor_header),
            resource_type="evidence_item",
            resource_id=evidence_id,
            resource_name=evidence.get("title"),
            metadata={"deleted_at": evidence.get("deleted_at")},
        )
        return evidence
    except EvidenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/evidence/{evidence_id}/review")
async def review_evidence(
    evidence_id: str,
    request: EvidenceReviewRequest,
    db: Session = Depends(get_tenant_session),
    current_tenant: str = Depends(get_current_tenant),
    token_payload: dict[str, Any] = Depends(get_current_payload),
    override_tenant: Optional[str] = Header(None, alias="X-Tenant-ID"),
    actor_header: Optional[str] = Header(None, alias="X-User-ID"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    workflow_service=Depends(get_compliance_agent_workflow_service),
):
    """Record a review decision for a durable evidence item."""
    _require_role(token_payload, REVIEW_ROLES)
    resolved_tenant_id = _resolve_tenant_id(current_tenant, override_tenant, request.tenant_id)
    try:
        reviewed = evidence_repository.review_evidence_item(
            db,
            resolved_tenant_id,
            evidence_id,
            _request_payload(request),
            actor_id=_actor_id(token_payload, actor_header),
        )
        reviewed_evidence = reviewed.get("evidence") or {}
        await _audit_evidence_event(
            action="evidence_retired" if request.review_status == "retired" else "evidence_reviewed",
            tenant_id=resolved_tenant_id,
            actor_user_id=_actor_id(token_payload, actor_header),
            resource_type="evidence_item",
            resource_id=evidence_id,
            resource_name=reviewed_evidence.get("title"),
            metadata={
                "review_status": request.review_status,
                "reviewer": (reviewed.get("review") or {}).get("reviewer"),
            },
        )
        if request.review_status == "expired":
            evidence = reviewed.get("evidence") or reviewed.get("item") or reviewed
            if isinstance(evidence, dict):
                recommendation = build_evidence_expiration_recommendation(evidence, expired=True)
                try:
                    await workflow_service.create_recommendation_and_task(
                        db,
                        tenant_id=resolved_tenant_id,
                        created_by=_actor_id(token_payload, actor_header),
                        authorization=authorization,
                        metadata={"evidence_review": reviewed},
                        **recommendation,
                    )
                except Exception as exc:  # pragma: no cover - recommendation triggers are side effects.
                    logger.warning(
                        "Failed to trigger Compliance Agent evidence review recommendation for tenant %s evidence %s: %s",
                        resolved_tenant_id,
                        evidence_id,
                        exc,
                    )
        return reviewed
    except EvidenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
