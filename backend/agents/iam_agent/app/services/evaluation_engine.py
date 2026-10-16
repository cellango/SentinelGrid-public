"""Entitlement evaluation engine for access decisions."""

import logging
import re
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.entitlement import Entitlement
from app.services.redis_cache import cache
from app.services.audit_logger import AuditLogger
from app.services.policy_service import PolicyService
from app.models.policies import EvaluationContext as PolicyContext

logger = logging.getLogger(__name__)


class EvaluationContext:
    """Context for access evaluation requests."""
    
    def __init__(
        self,
        user_id: UUID,
        tenant_id: UUID,
        resource_type: str,
        resource_id: str,
        action: str,
        additional_context: Optional[Dict[str, Any]] = None,
        *,
        trusted_client_ip: Optional[str] = None,
        subject_roles: Optional[tuple[str, ...]] = None,
        actor_id: Optional[UUID] = None,
        actor_type: str = "user"
    ):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.action = action
        self.additional_context = additional_context or {}
        # Only the authenticated server adapter supplies subject facts and peer IP.
        self.actor_id = actor_id if actor_id is not None else (user_id if actor_type == "user" else None)
        self.actor_type = actor_type
        self.subject_roles = subject_roles
        self.client_ip = trusted_client_ip
        self.request_time = datetime.now(timezone.utc)
        self.user_agent = self.additional_context.get("user_agent")
        self.session_id = self.additional_context.get("session_id")


class EvaluationResult:
    """Result of an access evaluation."""
    
    def __init__(
        self,
        decision: str,  # "allow" or "deny"
        reason: str,
        matched_entitlements: Optional[List[Dict[str, Any]]] = None,
        evaluated_at: Optional[datetime] = None,
        audit_recorded: bool = False
    ):
        self.audit_recorded = audit_recorded
        self.decision = decision
        self.reason = reason
        self.matched_entitlements = matched_entitlements or []
        self.evaluated_at = evaluated_at or datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "decision": self.decision,
            "reason": self.reason,
            "matched_entitlements": self.matched_entitlements,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None
        }


class EvaluationEngine:
    """Engine for evaluating access requests against entitlements."""
    
    def __init__(self, db: Session, *, policy_db: Optional[Session] = None):
        """Initialize evaluation engine."""
        self.db = db
        self.policy_db = policy_db if policy_db is not None else db
    
    def _matches_pattern(self, pattern: str, value: str) -> bool:
        """
        Check if a value matches a pattern.
        Supports wildcards: '*' matches any sequence of characters.
        
        Examples:
        - 'alert:*:read' matches 'alert:123:read'
        - 'alert:*' matches 'alert:123'
        - '*' matches anything
        """
        if not isinstance(pattern, str) or not isinstance(value, str):
            return False
        return re.fullmatch(re.escape(pattern).replace(r"\*", ".*"), value) is not None

    def _matches_resource_pattern(self, entitlement: Entitlement, context: EvaluationContext) -> bool:
        """Check if entitlement matches the resource in context."""
        # Check resource_type
        if not self._matches_pattern(entitlement.resource_type, context.resource_type):
            return False
        
        # Check resource_id
        if not self._matches_pattern(entitlement.resource_id, context.resource_id):
            return False
        
        # Check action
        if entitlement.action != "*" and entitlement.action != context.action:
            return False
        
        return True
    
    def _check_entitlement_status(self, entitlement: Entitlement) -> bool:
        """Check if entitlement is currently active."""
        if entitlement.status != "active":
            return False
        
        # Check expiration
        if entitlement.expires_at:
            expiry = entitlement.expires_at
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry <= datetime.now(timezone.utc):
                return False
        
        return True
    
    def _check_context_policies(self, entitlement: Entitlement, context: EvaluationContext) -> bool:
        """
        Check context-based policies (time, IP, etc.).
        Currently supports basic checks; can be extended for complex policies.
        """
        metadata = entitlement.metadata_json if entitlement.metadata_json is not None else {}
        if not isinstance(metadata, dict):
            return False
        
        # Check IP restrictions (if specified)
        allowed_ips = metadata.get("allowed_ips", [])
        if not isinstance(allowed_ips, list) or any(not isinstance(ip, str) for ip in allowed_ips):
            return False
        if allowed_ips:
            if not context.client_ip or context.client_ip not in allowed_ips:
                return False
        
        # Check time restrictions (if specified)
        allowed_hours = metadata.get("allowed_hours", None)
        if allowed_hours is not None:
            if not isinstance(allowed_hours, list) or any(type(v) is not int or not 0 <= v <= 23 for v in allowed_hours):
                return False
            current_hour = context.request_time.hour
            if current_hour not in allowed_hours:
                return False
        
        # Check day restrictions (if specified)
        allowed_days = metadata.get("allowed_days", None)
        if allowed_days is not None:
            if not isinstance(allowed_days, list) or any(type(v) is not int or not 0 <= v <= 6 for v in allowed_days):
                return False
            current_day = context.request_time.weekday()  # 0=Monday, 6=Sunday
            if current_day not in allowed_days:
                return False
        
        return True
    
    def _find_matching_entitlements(self, context: EvaluationContext) -> List[Entitlement]:
        """Find all entitlements that match the access request."""
        # Build query for entitlements
        query = self.db.query(Entitlement).filter(
            Entitlement.tenant_id == context.tenant_id,
            Entitlement.granted_to_type == "user",
            Entitlement.granted_to_id == context.user_id,
            Entitlement.status == "active"
        )
        
        # Filter by action (exact match or wildcard)
        query = query.filter(
            or_(
                Entitlement.action == context.action,
                Entitlement.action == "*"
            )
        )
        
        # Get all candidate entitlements
        candidates = query.populate_existing().all()
        
        # Filter by resource pattern matching
        matching = []
        for entitlement in candidates:
            if self._matches_resource_pattern(entitlement, context):
                matching.append(entitlement)
        
        return matching
    
    def _decide(self, context: EvaluationContext) -> EvaluationResult:
        context.request_time = datetime.now(timezone.utc)
        candidates = self._find_matching_entitlements(context)
        valid_entitlements = [e for e in candidates
                              if e.tenant_id == context.tenant_id
                              and e.granted_to_type == "user" and e.granted_to_id == context.user_id
                              and self._matches_resource_pattern(e, context)
                              and self._check_entitlement_status(e)
                              and self._check_context_policies(e, context)]
        if not valid_entitlements:
            return EvaluationResult("deny", "No current entitlement satisfies the resource/context restrictions")

        policy_context = PolicyContext(
            user_id=str(context.user_id),
            roles=list(context.subject_roles) if context.subject_roles is not None else None,
            resource_type=context.resource_type, resource=context.resource_id, action=context.action,
            entitlement_ids=[str(e.id) for e in valid_entitlements],
            ip_address=context.client_ip, time_of_day=context.request_time.strftime("%H:%M"),
            day_of_week=("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")[context.request_time.weekday()],
        )
        policy_result = PolicyService(self.policy_db, context.tenant_id, "", load_seed_tenant=False).evaluate_all_policies(policy_context)
        if policy_result.result != "allow":
            # No request-body MFA/approval flags can fulfill these requirements.
            return EvaluationResult("deny", f"Policy {policy_result.result}: {policy_result.explanation}")

        matched = [{"id": str(e.id), "resource_type": e.resource_type,
                    "resource_id": e.resource_id, "action": e.action, "status": e.status}
                   for e in valid_entitlements]
        primary = valid_entitlements[0]
        primary.last_used_at = datetime.now(timezone.utc)
        primary.usage_count_90d = (primary.usage_count_90d or 0) + 1
        return EvaluationResult("allow", "Current entitlement and policy grant satisfy all evaluated restrictions", matched)

    async def evaluate(self, context: EvaluationContext, use_cache: bool = True) -> EvaluationResult:
        """Return allow only after usage and the decision event commit together.

        Decision caches remain disabled. Every deny/error also attempts a durable
        event. If persistence fails, return a deny marked unaudited; HTTP adapters
        must return unavailable, rather than claim a completed audited decision.
        """
        try:
            result = self._decide(context)
        except Exception:
            logger.exception("Authorization lookup failed; denying access")
            self.db.rollback()
            result = EvaluationResult("deny", "Authorization evaluation unavailable")
        try:
            AuditLogger(self.db).log_evaluation(
                user_id=context.user_id, tenant_id=context.tenant_id,
                resource_type=context.resource_type, resource_id=context.resource_id,
                action=context.action, decision=result.decision,
                matched_entitlements=result.matched_entitlements,
                context={"client_ip": context.client_ip, "request_time": context.request_time.isoformat(),
                         "subject_roles": context.subject_roles},
                actor_id=context.actor_id, actor_type=context.actor_type, reason=result.reason,
            )
            self.db.commit()
            result.audit_recorded = True
            return result
        except Exception:
            logger.exception("Authorization audit persistence failed; denying access")
            self.db.rollback()
            return EvaluationResult("deny", "Authorization audit unavailable")

    async def evaluate_batch(
        self,
        contexts: List[EvaluationContext],
        use_cache: bool = True
    ) -> List[EvaluationResult]:
        """Evaluate multiple access requests in batch."""
        results = []
        for context in contexts:
            result = await self.evaluate(context, use_cache=use_cache)
            results.append(result)
        return results
    
    def get_user_entitlements(
        self,
        user_id: UUID,
        tenant_id: UUID,
        resource_type: Optional[str] = None,
        action: Optional[str] = None
    ) -> List[Entitlement]:
        """Get all entitlements for a user (for UI display)."""
        query = self.db.query(Entitlement).filter(
            Entitlement.tenant_id == tenant_id,
            Entitlement.granted_to_type == "user",
            Entitlement.granted_to_id == user_id,
            Entitlement.status == "active"
        )
        
        if resource_type:
            query = query.filter(
                or_(
                    Entitlement.resource_type == resource_type,
                    Entitlement.resource_type == "*"
                )
            )
        
        if action:
            query = query.filter(
                or_(
                    Entitlement.action == action,
                    Entitlement.action == "*"
                )
            )
        
        return query.all()

