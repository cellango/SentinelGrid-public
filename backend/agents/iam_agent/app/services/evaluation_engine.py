"""Entitlement evaluation engine for access decisions."""

import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.entitlement import Entitlement
from app.services.redis_cache import cache
from app.services.audit_logger import AuditLogger

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
        additional_context: Optional[Dict[str, Any]] = None
    ):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.action = action
        self.additional_context = additional_context or {}
        # Extract common context values
        self.client_ip = self.additional_context.get("client_ip")
        self.request_time = self.additional_context.get("request_time", datetime.utcnow())
        self.user_agent = self.additional_context.get("user_agent")
        self.session_id = self.additional_context.get("session_id")


class EvaluationResult:
    """Result of an access evaluation."""
    
    def __init__(
        self,
        decision: str,  # "allow" or "deny"
        reason: str,
        matched_entitlements: Optional[List[Dict[str, Any]]] = None,
        evaluated_at: Optional[datetime] = None
    ):
        self.decision = decision
        self.reason = reason
        self.matched_entitlements = matched_entitlements or []
        self.evaluated_at = evaluated_at or datetime.utcnow()
    
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
    
    def __init__(self, db: Session):
        """Initialize evaluation engine."""
        self.db = db
    
    def _matches_pattern(self, pattern: str, value: str) -> bool:
        """
        Check if a value matches a pattern.
        Supports wildcards: '*' matches any sequence of characters.
        
        Examples:
        - 'alert:*:read' matches 'alert:123:read'
        - 'alert:*' matches 'alert:123'
        - '*' matches anything
        """
        if pattern == "*":
            return True
        
        # Convert pattern to regex-like matching
        # Simple implementation: split by '*' and check segments
        if "*" not in pattern:
            return pattern == value
        
        # Handle wildcard patterns
        parts = pattern.split("*")
        if not value.startswith(parts[0]):
            return False
        
        value_remaining = value[len(parts[0]):]
        for i, part in enumerate(parts[1:], 1):
            if part == "":
                # Trailing wildcard - matches rest
                return True
            if part not in value_remaining:
                return False
            value_remaining = value_remaining[value_remaining.index(part) + len(part):]
        
        # All parts matched
        return value_remaining == "" or parts[-1] == ""
    
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
        if entitlement.expires_at and entitlement.expires_at < datetime.utcnow():
            return False
        
        return True
    
    def _check_context_policies(self, entitlement: Entitlement, context: EvaluationContext) -> bool:
        """
        Check context-based policies (time, IP, etc.).
        Currently supports basic checks; can be extended for complex policies.
        """
        metadata = entitlement.metadata_json or {}
        
        # Check IP restrictions (if specified)
        allowed_ips = metadata.get("allowed_ips", [])
        if allowed_ips and context.client_ip:
            if context.client_ip not in allowed_ips:
                return False
        
        # Check time restrictions (if specified)
        allowed_hours = metadata.get("allowed_hours", None)
        if allowed_hours is not None:
            current_hour = context.request_time.hour
            if current_hour not in allowed_hours:
                return False
        
        # Check day restrictions (if specified)
        allowed_days = metadata.get("allowed_days", None)
        if allowed_days is not None:
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
        candidates = query.all()
        
        # Filter by resource pattern matching
        matching = []
        for entitlement in candidates:
            if self._matches_resource_pattern(entitlement, context):
                matching.append(entitlement)
        
        return matching
    
    async def evaluate(
        self,
        context: EvaluationContext,
        use_cache: bool = True
    ) -> EvaluationResult:
        """
        Evaluate an access request.
        
        Returns EvaluationResult with decision (allow/deny) and reason.
        """
        # Generate cache key
        cache_key = (
            f"evaluation:user:{context.user_id}:tenant:{context.tenant_id}:"
            f"resource:{context.resource_type}:{context.resource_id}:action:{context.action}"
        )
        
        # Try cache first
        if use_cache:
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for evaluation: {cache_key}")
                return EvaluationResult(
                    decision=cached_result["decision"],
                    reason=cached_result["reason"],
                    matched_entitlements=cached_result.get("matched_entitlements", []),
                    evaluated_at=datetime.fromisoformat(cached_result["evaluated_at"])
                )
        
        # Find matching entitlements
        matching_entitlements = self._find_matching_entitlements(context)
        
        if not matching_entitlements:
            result = EvaluationResult(
                decision="deny",
                reason="No matching entitlements found",
                matched_entitlements=[]
            )
            # Cache denial (shorter TTL)
            if use_cache:
                cache.set(cache_key, result.to_dict(), ttl=300)  # 5 minutes
            return result
        
        # Check each entitlement for status and context policies
        valid_entitlements = []
        for entitlement in matching_entitlements:
            if not self._check_entitlement_status(entitlement):
                continue
            
            if not self._check_context_policies(entitlement, context):
                continue
            
            valid_entitlements.append(entitlement)
        
        if not valid_entitlements:
            result = EvaluationResult(
                decision="deny",
                reason="No valid entitlements (expired or context restrictions)",
                matched_entitlements=[]
            )
            if use_cache:
                cache.set(cache_key, result.to_dict(), ttl=300)
            return result
        
        # Serialize matched entitlements
        matched_entitlements = [
            {
                "id": str(e.id),
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "action": e.action,
                "status": e.status
            }
            for e in valid_entitlements
        ]

        # At least one valid entitlement found - allow access
        # Update last_used_at and usage_count for the first matching entitlement
        primary_entitlement = valid_entitlements[0]
        primary_entitlement.last_used_at = datetime.utcnow()
        primary_entitlement.usage_count_90d = (primary_entitlement.usage_count_90d or 0) + 1
        
        try:
            self.db.commit()
            
            # Audit log the evaluation
            audit_logger = AuditLogger(self.db)
            audit_logger.log_evaluation(
                user_id=context.user_id,
                tenant_id=context.tenant_id,
                resource_type=context.resource_type,
                resource_id=context.resource_id,
                action=context.action,
                decision="allow",
                matched_entitlements=matched_entitlements,
                context=context.additional_context
            )
        except Exception as e:
            logger.error(f"Failed to update entitlement usage: {e}")
            self.db.rollback()
        
        result = EvaluationResult(
            decision="allow",
            reason=f"Access granted by {len(valid_entitlements)} entitlement(s)",
            matched_entitlements=matched_entitlements
        )
        
        # Cache result
        if use_cache:
            cache.set(cache_key, result.to_dict(), ttl=3600)  # 1 hour
        
        return result
    
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

