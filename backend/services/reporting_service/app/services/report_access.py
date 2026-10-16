"""Report access-control and audit helpers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.report import Report, ReportTemplate
from app.services.audit_client import AuditClient

logger = logging.getLogger(__name__)


ROLE_BYPASS = {"admin", "superadmin", "super_admin", "tenant_admin"}


def normalize_role(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def roles_from_payload(token_payload: dict[str, Any] | None) -> set[str]:
    payload = token_payload or {}
    roles = payload.get("roles") or payload.get("realm_roles") or []
    return {normalize_role(role) for role in roles if normalize_role(role)}


def actor_id_from_payload(
    token_payload: dict[str, Any] | None,
    fallback: str = "authenticated_user",
) -> str:
    payload = token_payload or {}
    return (
        payload.get("user_id")
        or payload.get("sub")
        or payload.get("preferred_username")
        or payload.get("email")
        or fallback
    )


def enforce_template_roles(
    template: ReportTemplate,
    token_payload: dict[str, Any] | None,
) -> None:
    """Enforce template required_roles against the authenticated user payload."""
    if template_roles_satisfied(template, token_payload):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Required report template role not found",
    )


def template_roles_satisfied(
    template: ReportTemplate,
    token_payload: dict[str, Any] | None,
) -> bool:
    """Return whether the authenticated payload can use a report template."""
    required_roles = {
        normalize_role(role)
        for role in (getattr(template, "required_roles", None) or [])
    }
    required_roles.discard("")
    if not required_roles:
        return True

    user_roles = roles_from_payload(token_payload)
    if user_roles.intersection(required_roles) or user_roles.intersection(ROLE_BYPASS):
        return True
    return False


def enforce_report_template_roles(
    db: Session,
    report: Report,
    token_payload: dict[str, Any] | None,
) -> None:
    """Enforce the source template roles for an existing report when possible."""
    template_id = getattr(report, "template_id", None)
    if not template_id:
        return

    template = db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()
    if template:
        enforce_template_roles(template, token_payload)


async def audit_report_event(
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
    """Best-effort audit event for report access lifecycle actions."""
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
        logger.warning("Failed to audit report event %s for %s: %s", action, resource_id, exc)
