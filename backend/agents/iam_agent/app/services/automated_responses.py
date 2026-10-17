"""
Automated Risk Response Service
Legacy response methods are blocked; local risk analysis remains experimental.
"""

from app.services.itdr_service import block_legacy_response

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

from app.services.keycloak_client import KeycloakClient
from app.services.anomaly_detection import AnomalyDetectionService
from app.services.risk_scoring import RiskScoringService

logger = logging.getLogger(__name__)


class ResponseAction(str, Enum):
    """Types of automated response actions."""
    ALERT_ONLY = "alert_only"
    REVOKE_ACCESS = "revoke_access"
    DISABLE_USER = "disable_user"
    REQUIRE_MFA = "require_mfa"
    ESCALATE = "escalate"
    LOG_ONLY = "log_only"


class AutomatedResponseService:
    """Service for automated risk responses."""
    
    def __init__(
        self,
        keycloak_client: KeycloakClient,
        anomaly_service: Optional[AnomalyDetectionService] = None,
        risk_service: Optional[RiskScoringService] = None
    ):
        self.keycloak_client = keycloak_client
        self.anomaly_service = anomaly_service
        self.risk_service = risk_service
        
        # Default response policies
        self.response_policies = {
            "critical_risk": ResponseAction.DISABLE_USER,
            "high_risk": ResponseAction.REVOKE_ACCESS,
            "critical_anomaly": ResponseAction.REVOKE_ACCESS,
            "privilege_escalation": ResponseAction.ALERT_ONLY,
            "geographic_anomaly": ResponseAction.REQUIRE_MFA,
            "suspicious_access": ResponseAction.ALERT_ONLY
        }
    
    def process_risk_response(
        self,
        user_id: str,
        risk_score: float,
        risk_level: str,
        anomalies: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
        auto_remediate: bool = False
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    def auto_revoke_suspicious_access(
        self,
        user_id: str,
        anomalies: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    def auto_flag_high_risk_activities(
        self,
        user_id: str,
        activities: List[Dict[str, Any]],
        risk_threshold: float = 70.0,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Automatically flag high-risk activities for review.
        """
        flagged_activities = []
        
        for activity in activities:
            # Calculate activity risk (simplified - could use more sophisticated logic)
            activity_risk = 0
            
            resource = activity.get("resource") or activity.get("resource_type", "")
            if any(kw in resource.upper() for kw in ["PROD", "PII", "SECRET", "ADMIN"]):
                activity_risk += 30
            
            action = activity.get("action", "").upper()
            if action in ["DELETE", "MODIFY", "GRANT", "REVOKE"]:
                activity_risk += 20
            
            # Check if outside normal hours
            timestamp = activity.get("timestamp")
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                    hour = dt.hour
                    if hour < 6 or hour > 22:  # Outside 6 AM - 10 PM
                        activity_risk += 15
                except:
                    pass
            
            if activity_risk >= risk_threshold:
                flagged_activities.append({
                    "activity": activity,
                    "risk_score": activity_risk,
                    "flagged_at": datetime.utcnow().isoformat(),
                    "reason": "High-risk activity detected"
                })
        
        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "total_activities": len(activities),
            "flagged_count": len(flagged_activities),
            "flagged_activities": flagged_activities,
            "flagged_at": datetime.utcnow().isoformat()
        }
    
    def generate_alert(
        self,
        alert_type: str,
        user_id: Optional[str],
        details: Dict[str, Any],
        tenant_id: Optional[str] = None,
        severity: str = "medium"
    ) -> Dict[str, Any]:
        """
        Generate an alert for security events.
        """
        alert = {
            "alert_type": alert_type,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "severity": severity,
            "details": details,
            "created_at": datetime.utcnow().isoformat(),
            "status": "new"
        }
        
        # TODO: Send alert to alerting system (SIEM, notification service, etc.)
        logger.warning(f"Security alert: {alert_type} for user {user_id}")
        
        return alert
    
    def _execute_action(
        self,
        action: ResponseAction,
        user_id: str,
        tenant_id: Optional[str],
        reason: str,
        auto_remediate: bool = False
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    def _get_action_priority(self, action: ResponseAction) -> int:
        """Get priority level for action (higher = more severe)."""
        priorities = {
            ResponseAction.LOG_ONLY: 1,
            ResponseAction.ALERT_ONLY: 2,
            ResponseAction.REQUIRE_MFA: 3,
            ResponseAction.REVOKE_ACCESS: 4,
            ResponseAction.DISABLE_USER: 5,
            ResponseAction.ESCALATE: 5
        }
        return priorities.get(action, 0)

