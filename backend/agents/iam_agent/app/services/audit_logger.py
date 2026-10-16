"""Transaction-coupled IAM events. Failures propagate; callers own the commit."""
import json
from uuid import UUID, uuid4
from fastapi import Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from app.models.entitlement import Entitlement
from app.models.audit_event import IAMAuditEvent
from app.api.request_context import get_entitlement_session


def _snapshot(value):
    def redact(data):
        if isinstance(data, dict):
            return {key: "[REDACTED]" if any(part in key.lower() for part in
                    ("token", "password", "secret", "authorization", "cookie")) else redact(item)
                    for key, item in data.items()}
        if isinstance(data, list):
            return [redact(item) for item in data]
        return data
    result = redact(jsonable_encoder(value))
    if len(json.dumps(result, allow_nan=False).encode()) > 65536:
        raise ValueError("Audit payload exceeds the bounded event size")
    return result


class AuditLogger:
    def __init__(self, db: Session):
        self.db = db

    def log_entitlement_event(self, event_type, entitlement_id, tenant_id, performed_by,
                              performed_by_name=None, changes=None, reason=None,
                              campaign_id=None, certification_id=None, metadata=None,
                              *, actor_type="user", subject_id=None, decision=None):
        tenant = UUID(str(tenant_id))
        actor = UUID(str(performed_by)) if performed_by is not None else None
        if actor_type not in {"user", "internal_service"} or (actor_type == "user" and actor is None):
            raise ValueError("An authenticated audit actor is required")
        row = IAMAuditEvent(
            id=uuid4(), tenant_id=tenant, event_type=event_type, entitlement_id=entitlement_id,
            performed_by=actor, actor_type=actor_type, subject_id=subject_id, decision=decision,
            performed_by_name=performed_by_name, changes=_snapshot(changes or {}), reason=reason,
            campaign_id=campaign_id, certification_id=certification_id,
            metadata_json=_snapshot(metadata or {}),
        )
        self.db.add(row)
        self.db.flush()
        return row

    def log_evaluation(self, user_id, tenant_id, resource_type, resource_id, action, decision,
                       matched_entitlements=None, context=None, *, actor_id=None,
                       actor_type="user", reason=None):
        if decision not in {"allow", "deny"}:
            raise ValueError("Unsupported authorization decision")
        return self.log_entitlement_event(
            "evaluated", None, tenant_id, actor_id, actor_type=actor_type,
            subject_id=user_id, decision=decision, reason=reason,
            changes={"resource_type": resource_type, "resource_id": resource_id,
                     "action": action, "decision": decision},
            metadata={"context": context or {}, "matched_entitlements": matched_entitlements or []},
        )

    def log_entitlement_created(
        self,
        entitlement: Entitlement,
        performed_by: UUID,
        performed_by_name: str | None = None,
        reason: str | None = None
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
        old_values: dict,
        new_values: dict,
        reason: str | None = None
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
        reason: str | None = None
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


def get_audit_logger(db: Session = Depends(get_entitlement_session)) -> AuditLogger:
    """
    Factory function for AuditLogger dependency injection.
    
    Usage in FastAPI endpoints:
        @router.post("/endpoint")
        async def endpoint(audit_logger: AuditLogger = Depends(get_audit_logger)):
            audit_logger.log_entitlement_event(...)
    """
    return AuditLogger(db)

