"""
Centralized Audit Logger for SentinelGrid
Provides consistent audit logging across all services for compliance (SOC 2, HIPAA, PCI)
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
import json
from enum import Enum

logger = logging.getLogger(__name__)


class AuditAction(str, Enum):
    """Standard audit actions."""
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_RESET = "password_reset"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    
    # IAM Operations
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_ENABLED = "user_enabled"
    USER_DISABLED = "user_disabled"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"
    ENTITLEMENT_GRANTED = "entitlement_granted"
    ENTITLEMENT_REVOKED = "entitlement_revoked"
    
    # Access Reviews
    ACCESS_REVIEW_STARTED = "access_review_started"
    ACCESS_REVIEW_COMPLETED = "access_review_completed"
    ACCESS_APPROVED = "access_approved"
    ACCESS_REVOKED_REVIEW = "access_revoked_review"
    
    # Configuration
    CONFIG_CHANGED = "config_changed"
    POLICY_CREATED = "policy_created"
    POLICY_UPDATED = "policy_updated"
    POLICY_DELETED = "policy_deleted"
    
    # Data Operations
    DATA_ACCESSED = "data_accessed"
    DATA_EXPORTED = "data_exported"
    DATA_DELETED = "data_deleted"
    
    # Compliance
    REPORT_GENERATED = "report_generated"
    REPORT_DOWNLOADED = "report_downloaded"
    EVIDENCE_COLLECTED = "evidence_collected"
    COMPLIANCE_CHECK = "compliance_check"

    # Workflow orchestration
    INCIDENT_CREATED = "incident_created"
    INCIDENT_TICKET_REQUESTED = "incident_ticket_requested"
    TICKET_CREATED = "ticket_created"
    TICKET_HANDOFF_COMPLETED = "ticket_handoff_completed"
    TICKET_HANDOFF_SKIPPED = "ticket_handoff_skipped"
    NOTIFICATION_SENT = "notification_sent"
    WORKFLOW_FAILED = "workflow_failed"


class AuditCategory(str, Enum):
    """Audit event categories."""
    AUTH = "auth"
    IAM = "iam"
    CONFIG = "config"
    DATA = "data"
    COMPLIANCE = "compliance"
    SECURITY = "security"

    # Incident / ticket lifecycle
    INCIDENT_CREATED = "incident_created"
    INCIDENT_DEDUPED = "incident_deduped"
    INCIDENT_SUPPRESSED = "incident_suppressed"
    TICKET_CREATED = "ticket_created"


class AuditLogger:
    """Centralized audit logger for compliance."""
    
    def __init__(self, db_session=None):
        """
        Initialize audit logger.
        
        Args:
            db_session: SQLAlchemy session for database logging
        """
        self.db = db_session
        self.logger = logging.getLogger("sentinelgrid.audit")
    
    def log(
        self,
        action: AuditAction,
        tenant_id: UUID,
        realm_name: str,
        actor_user_id: str,
        actor_email: Optional[str] = None,
        actor_roles: Optional[List[str]] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None,
        changes: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[UUID]:
        """
        Log an audit event.
        
        Args:
            action: The action being audited
            tenant_id: Tenant ID
            realm_name: Keycloak realm name
            actor_user_id: User performing the action
            actor_email: Actor's email
            actor_roles: Actor's roles
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            resource_name: Name of resource
            before_state: State before the action
            after_state: State after the action
            changes: Specific changes made
            success: Whether the action succeeded
            error_message: Error message if failed
            ip_address: IP address of requester
            user_agent: User agent string
            request_id: Request correlation ID
            session_id: Session ID
            metadata: Additional metadata
            
        Returns:
            UUID of the audit log entry, or None if logging failed
        """
        # Determine category from action
        category = self._get_category(action)
        
        # Calculate changes if not provided
        if changes is None and before_state and after_state:
            changes = self._calculate_changes(before_state, after_state)
        
        # Log to application logger (always, even if DB fails)
        log_entry = {
            "action": action.value,
            "category": category.value,
            "tenant_id": str(tenant_id),
            "realm": realm_name,
            "actor": actor_user_id,
            "resource": f"{resource_type}:{resource_id}" if resource_type and resource_id else None,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if success:
            self.logger.info(f"AUDIT: {json.dumps(log_entry)}")
        else:
            log_entry["error"] = error_message
            self.logger.warning(f"AUDIT_FAILED: {json.dumps(log_entry)}")
        
        # Log to database if session provided
        if self.db:
            try:
                from sqlalchemy import text
                
                query = text("""
                    INSERT INTO audit.platform_audit_logs (
                        tenant_id, realm_name, action, action_category,
                        actor_user_id, actor_email, actor_roles,
                        resource_type, resource_id, resource_name,
                        before_state, after_state, changes,
                        success, error_message,
                        ip_address, user_agent, request_id, session_id,
                        metadata, timestamp
                    ) VALUES (
                        :tenant_id, :realm_name, :action, :action_category,
                        :actor_user_id, :actor_email, :actor_roles,
                        :resource_type, :resource_id, :resource_name,
                        :before_state, :after_state, :changes,
                        :success, :error_message,
                        :ip_address, :user_agent, :request_id, :session_id,
                        :metadata, :timestamp
                    )
                    RETURNING id
                """)
                
                result = self.db.execute(query, {
                    "tenant_id": str(tenant_id),
                    "realm_name": realm_name,
                    "action": action.value,
                    "action_category": category.value,
                    "actor_user_id": actor_user_id,
                    "actor_email": actor_email,
                    "actor_roles": actor_roles,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "resource_name": resource_name,
                    "before_state": json.dumps(before_state) if before_state else None,
                    "after_state": json.dumps(after_state) if after_state else None,
                    "changes": json.dumps(changes) if changes else None,
                    "success": success,
                    "error_message": error_message,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "request_id": request_id,
                    "session_id": session_id,
                    "metadata": json.dumps(metadata) if metadata else None,
                    "timestamp": datetime.utcnow()
                })
                
                self.db.commit()
                audit_id = result.fetchone()[0]
                if isinstance(audit_id, UUID):
                    return audit_id
                try:
                    return UUID(str(audit_id))
                except Exception:
                    self.logger.error("Failed to coerce audit_id to UUID")
                    return None
                
            except Exception as e:
                self.logger.error(f"Failed to write audit log to database: {e}", exc_info=True)
                # Don't raise - audit logging should never break the application
                return None
        
        return None
    
    def _get_category(self, action: AuditAction) -> AuditCategory:
        """Determine category from action."""
        action_value = action.value
        
        if action_value.startswith(("login", "logout", "password", "mfa")):
            return AuditCategory.AUTH
        elif action_value.startswith(("user_", "role_", "entitlement_", "access_")):
            return AuditCategory.IAM
        elif action_value.startswith(("config_", "policy_")):
            return AuditCategory.CONFIG
        elif action_value.startswith("data_"):
            return AuditCategory.DATA
        elif action_value.startswith(("report_", "evidence_", "compliance_")):
            return AuditCategory.COMPLIANCE
        else:
            return AuditCategory.SECURITY
    
    def _calculate_changes(
        self,
        before_state: Dict[str, Any],
        after_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate what changed between before and after states."""
        changes = {}
        
        # Find all keys in either state
        all_keys = set(before_state.keys()) | set(after_state.keys())
        
        for key in all_keys:
            before_value = before_state.get(key)
            after_value = after_state.get(key)
            
            if before_value != after_value:
                changes[key] = {
                    "before": before_value,
                    "after": after_value
                }
        
        return changes
    
    def log_login(
        self,
        tenant_id: UUID,
        realm_name: str,
        user_id: str,
        email: str,
        success: bool = True,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log a login attempt."""
        return self.log(
            action=AuditAction.LOGIN if success else AuditAction.LOGIN_FAILED,
            tenant_id=tenant_id,
            realm_name=realm_name,
            actor_user_id=user_id,
            actor_email=email,
            success=success,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_user_change(
        self,
        action: AuditAction,
        tenant_id: UUID,
        realm_name: str,
        actor_user_id: str,
        target_user_id: str,
        target_user_email: str,
        before_state: Optional[Dict] = None,
        after_state: Optional[Dict] = None
    ):
        """Log a user management action."""
        return self.log(
            action=action,
            tenant_id=tenant_id,
            realm_name=realm_name,
            actor_user_id=actor_user_id,
            resource_type="user",
            resource_id=target_user_id,
            resource_name=target_user_email,
            before_state=before_state,
            after_state=after_state
        )
    
    def log_report_access(
        self,
        tenant_id: UUID,
        realm_name: str,
        user_id: str,
        user_email: str,
        report_id: UUID,
        report_name: str,
        access_type: str,  # 'generated', 'viewed', 'downloaded_pdf', 'downloaded_csv'
        ip_address: Optional[str] = None
    ):
        """Log report access for compliance."""
        action = AuditAction.REPORT_GENERATED if access_type == 'generated' else AuditAction.REPORT_DOWNLOADED
        
        return self.log(
            action=action,
            tenant_id=tenant_id,
            realm_name=realm_name,
            actor_user_id=user_id,
            actor_email=user_email,
            resource_type="report",
            resource_id=str(report_id),
            resource_name=report_name,
            ip_address=ip_address,
            metadata={"access_type": access_type}
        )


# Singleton instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(db_session=None) -> AuditLogger:
    """Get or create the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None or db_session is not None:
        _audit_logger = AuditLogger(db_session)
    return _audit_logger
