import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import enforce_org_scope, get_internal_org_id, require_internal_service_token
from app import models, schemas
from app.services.platform_alert_forwarder import forward_event_to_platform
from app.services.siem_export_manager import get_siem_export_manager

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/events")
def ingest_event(
    event: schemas.TelemetryEventCreate,
    background_tasks: BackgroundTasks,
    _: str = Depends(require_internal_service_token),
    current_org_id: UUID = Depends(get_internal_org_id),
    db: Session = Depends(get_db),
):
    """Ingest AI event from gateway"""
    enforce_org_scope(current_org_id, event.org_id)
    db_event = models.AiEvent(
        org_id=event.org_id,
        ai_app_id=_coerce_uuid(event.ai_app_id),
        user_id=event.user_id,
        provider=event.provider,
        model=event.model,
        has_pii=event.has_pii,
        has_secrets=event.has_secrets,
        prompt_injection_suspected=event.prompt_injection_suspected,
        policy_decision=event.policy_decision,
        tokens_in=event.tokens_in,
        tokens_out=event.tokens_out
    )
    db.add(db_event)
    db.commit()

    if settings.SIEM_EXPORT_ENABLED:
        background_tasks.add_task(_dispatch_siem_export, event.model_copy(deep=True))
    if settings.PLATFORM_ALERT_INGEST_ENABLED:
        background_tasks.add_task(_dispatch_platform_alert_ingest, event.model_copy(deep=True))

    return {"status": "ingested"}

@router.post("/tool-calls")
def ingest_tool_call(
    tool_call: dict,
    _: str = Depends(require_internal_service_token),
    current_org_id: UUID = Depends(get_internal_org_id),
):
    """Ingest AI tool call from gateway"""
    org_id = tool_call.get("org_id")
    if org_id not in (None, "", "default"):
        enforce_org_scope(current_org_id, org_id)
    # TODO: Implement tool call storage
    return {"status": "ingested"}


def _coerce_uuid(value: object) -> UUID | None:
    if value in (None, "", "default"):
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def _dispatch_siem_export(event: schemas.TelemetryEventCreate) -> None:
    try:
        results = get_siem_export_manager().export_ai_event(event)
        failed = [result for result in results if not result.success]
        if failed:
            logger.warning(
                "SIEM export finished with %s failed destination(s): %s",
                len(failed),
                ", ".join(result.destination_name for result in failed),
            )
    except Exception:
        logger.exception("Unhandled exception during SIEM export dispatch")


def _dispatch_platform_alert_ingest(event: schemas.TelemetryEventCreate) -> None:
    try:
        result = forward_event_to_platform(event)
        if result and result.get("status") == "skipped":
            logger.debug("Platform alert ingest skipped low-signal AI event %s", event.event_id or "unknown")
    except Exception:
        logger.exception("Unhandled exception during platform alert ingest dispatch")
