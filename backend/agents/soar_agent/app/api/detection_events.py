"""Detection event webhook endpoint for SOAR agent."""

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sg_core.service_security import verify_internal_service_token
from sqlalchemy.orm import Session

from app.core.database import get_tenant_db
from app.core.config import settings
from app.services.incident_creator import IncidentCreator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/detection-events", tags=["detection-events"])


async def validate_webhook_auth(
    authorization: Optional[str] = Header(None),
    x_internal_service_token: Optional[str] = Header(None, alias="X-Internal-Service-Token"),
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token"),
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
) -> UUID:
    """
    Validate detection-event ingestion as authenticated internal-only traffic.
    """
    verify_internal_service_token(
        settings.INTERNAL_SERVICE_TOKEN,
        authorization=authorization,
        x_internal_service_token=x_internal_service_token,
        x_internal_token=x_internal_token,
        missing_detail="Missing or invalid authorization header",
        invalid_detail="Invalid internal service token",
    )

    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Tenant-ID header"
        )

    try:
        return UUID(str(x_tenant_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Tenant-ID header format",
        ) from exc


def get_webhook_tenant_session(
    tenant_id: UUID = Depends(validate_webhook_auth),
):
    yield from get_tenant_db(tenant_id)


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_detection_event(
    detection_event: Dict[str, Any],
    tenant_id: UUID = Depends(validate_webhook_auth),
    db: Session = Depends(get_webhook_tenant_session),
):
    """
    Webhook endpoint to receive detection events from OpenSearch monitors.
    
    This endpoint is called by OpenSearch Alerting when a detection rule fires.
    It creates an incident in SOAR and optionally triggers a playbook.
    
    Headers:
        Authorization: Bearer {INTERNAL_SERVICE_TOKEN}
        X-Tenant-ID: {tenant_uuid}
    
    Body:
        Detection event data from OpenSearch monitor
    
    Returns:
        Dict with incident_id and status
    """
    try:
        logger.info(
            f"Received detection event webhook for tenant {tenant_id}, "
            f"alert_type={detection_event.get('sg', {}).get('alert_type')}"
        )
        
        # Extract critical fields
        sg_context = detection_event.get("sg", {})
        if not sg_context:
            raise ValueError("Missing 'sg' context in detection event")
        
        alert_type = sg_context.get("alert_type")
        severity = sg_context.get("severity")
        
        if not alert_type:
            raise ValueError("Missing alert_type in detection event")
        
        # Validate tenant_id matches
        event_tenant_id = sg_context.get("tenant_id")
        if event_tenant_id is None:
            raise ValueError("Missing tenant_id in detection event")

        try:
            event_tenant_uuid = UUID(str(event_tenant_id))
        except ValueError as exc:
            raise ValueError("Invalid tenant_id in detection event") from exc

        if event_tenant_uuid != tenant_id:
            raise ValueError(
                f"Tenant ID mismatch: event={event_tenant_uuid}, header={tenant_id}"
            )
        
        # Create incident from detection event
        incident_creator = IncidentCreator(db)
        result = await incident_creator.create_incident_from_detection(
            detection_event=detection_event,
            tenant_id=str(tenant_id)
        )
        
        logger.info(
            f"Created incident {result['incident_id']} from detection event, "
            f"alert_type={alert_type}, severity={severity}"
        )
        
        return {
            "status": "accepted",
            "incident_id": result["incident_id"],
            "playbook_execution_id": result.get("playbook_execution_id"),
            "message": "Detection event processed successfully"
        }
        
    except ValueError as e:
        logger.error(f"Validation error processing detection event: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing detection event: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process detection event: {str(e)}"
        )


@router.get("/health")
async def detection_webhook_health():
    """Health check for detection webhook endpoint."""
    return {
        "status": "ok",
        "endpoint": "/detection-events/ingest",
        "description": "Detection event webhook receiver"
    }
