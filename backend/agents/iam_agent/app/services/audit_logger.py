"""Audit logging service for entitlement operations."""

import logging
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import Depends

from app.models.entitlement import Entitlement
from app.core.database import get_db

logger = logging.getLogger(__name__)


class AuditLogger:
    """Service for logging entitlement operations to audit log."""
    
    def __init__(self, db: Session):
        """Initialize audit logger."""
        self.db = db
    
    def log_entitlement_event(
        self,
        event_type: str,  # 'created', 'updated', 'status_change', 'granted', 'revoked', 'expired', 'evaluated'
        entitlement_id: Optional[UUID],
        tenant_id: UUID,
        performed_by: UUID,
        performed_by_name: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
        campaign_id: Optional[UUID] = None,
        certification_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log an entitlement event to the audit log.
        
        For now, logs to application logs and database.
        Future: Add dedicated audit_log table if needed.
        """
        log_entry = {
            "event_type": event_type,
            "entitlement_id": str(entitlement_id) if entitlement_id else None,
            "tenant_id": str(tenant_id),
            "performed_by": str(performed_by),
            "performed_by_name": performed_by_name,
            "timestamp": datetime.utcnow().isoformat(),
            "changes": changes or {},
            "reason": reason,
            "campaign_id": str(campaign_id) if campaign_id else None,
            "certification_id": str(certification_id) if certification_id else None,
            "metadata": metadata or {}
        }
        
        # Log to application logs
        logger.info(
            f"Audit: {event_type} | "
            f"Entitlement: {entitlement_id} | "
            f"Tenant: {tenant_id} | "
            f"By: {performed_by} | "
            f"Reason: {reason or 'N/A'}"
        )
        
        # TODO: Store in entitlement_audit_log table
        # For now, structured logging is sufficient for Phase 4
        
        return log_entry
    
    def log_evaluation(
        self,
        user_id: UUID,
        tenant_id: UUID,
        resource_type: str,
        resource_id: str,
        action: str,
        decision: str,
        matched_entitlements: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log an authorization evaluation."""
        self.log_entitlement_event(
            event_type="evaluated",
            entitlement_id=None,
            tenant_id=tenant_id,
            performed_by=user_id,
            changes={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
                "decision": decision,
                "matched_entitlements_count": len(matched_entitlements) if matched_entitlements else 0
            },
            reason=f"Authorization evaluation: {decision}",
            metadata={
                "context": context or {},
                "matched_entitlements": matched_entitlements or []
            }
        )
    
    def log_entitlement_created(
        self,
        entitlement: Entitlement,
        performed_by: UUID,
        performed_by_name: Optional[str] = None,
        reason: Optional[str] = None
    ):
        """Log entitlement creation."""
        self.log_entitlement_event(
            event_type="created",
            entitlement_id=entitlement.id,
            tenant_id=entitlement.tenant_id,
            performed_by=performed_by,
            performed_by_name=performed_by_name,
            changes={
                "resource_type": entitlement.resource_type,
                "resource_id": entitlement.resource_id,
                "action": entitlement.action,
                "granted_to_type": entitlement.granted_to_type,
                "granted_to_id": str(entitlement.granted_to_id)
            },
            reason=reason or "Entitlement created"
        )
    
    def log_entitlement_updated(
        self,
        entitlement: Entitlement,
        performed_by: UUID,
        old_values: Dict[str, Any],
        new_values: Dict[str, Any],
        reason: Optional[str] = None
    ):
        """Log entitlement update."""
        changes = {
            field: {"old": old_values.get(field), "new": new_values.get(field)}
            for field in set(old_values.keys()) | set(new_values.keys())
            if old_values.get(field) != new_values.get(field)
        }
        
        self.log_entitlement_event(
            event_type="updated",
            entitlement_id=entitlement.id,
            tenant_id=entitlement.tenant_id,
            performed_by=performed_by,
            changes=changes,
            reason=reason or "Entitlement updated"
        )
    
    def log_entitlement_revoked(
        self,
        entitlement: Entitlement,
        performed_by: UUID,
        reason: Optional[str] = None
    ):
        """Log entitlement revocation."""
        self.log_entitlement_event(
            event_type="revoked",
            entitlement_id=entitlement.id,
            tenant_id=entitlement.tenant_id,
            performed_by=performed_by,
            changes={"status": {"old": entitlement.status, "new": "revoked"}},
            reason=reason or "Entitlement revoked"
        )


def get_audit_logger(db: Session = Depends(get_db)) -> AuditLogger:
    """
    Factory function for AuditLogger dependency injection.
    
    Usage in FastAPI endpoints:
        @router.post("/endpoint")
        async def endpoint(audit_logger: AuditLogger = Depends(get_audit_logger)):
            audit_logger.log_entitlement_event(...)
    """
    return AuditLogger(db)

