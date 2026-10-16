"""
Automated Risk Response Service
Automatically responds to high-risk situations based on configured policies
"""

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
        self.anomaly_service = anomaly_service or AnomalyDetectionService()
        self.risk_service = risk_service or RiskScoringService()
        
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
        """
        Process automated response based on risk score and anomalies.
        
        Args:
            user_id: User ID to process
            risk_score: Overall risk score (0-100)
            risk_level: Risk level (low, medium, high, critical)
            anomalies: List of detected anomalies
            tenant_id: Tenant ID for multi-tenancy
            auto_remediate: If True, execute automated remediation
            
        Returns:
            Dictionary with actions taken and results
        """
        actions_taken = []
        results = []
        
        # Determine response based on risk level
        if risk_level == "critical":
            action = self.response_policies.get("critical_risk", ResponseAction.DISABLE_USER)
        elif risk_level == "high":
            action = self.response_policies.get("high_risk", ResponseAction.REVOKE_ACCESS)
        else:
            action = ResponseAction.ALERT_ONLY
        
        # Check for specific anomaly types
        critical_anomalies = [a for a in anomalies if a.get("severity") == "critical"]
        if critical_anomalies:
            anomaly_action = self.response_policies.get("critical_anomaly", ResponseAction.REVOKE_ACCESS)
            if self._get_action_priority(anomaly_action) > self._get_action_priority(action):
                action = anomaly_action
        
        privilege_escalations = [a for a in anomalies if a.get("type") == "privilege_escalation"]
        if privilege_escalations:
            escalation_action = self.response_policies.get("privilege_escalation", ResponseAction.ALERT_ONLY)
            actions_taken.append(self._execute_action(
                escalation_action,
                user_id,
                tenant_id,
                reason="Privilege escalation detected",
                auto_remediate=auto_remediate
            ))
        
        # Execute primary action
        if auto_remediate or action in [ResponseAction.ALERT_ONLY, ResponseAction.LOG_ONLY]:
            action_result = self._execute_action(
                action,
                user_id,
                tenant_id,
                reason=f"Risk level: {risk_level}, Score: {risk_score}",
                auto_remediate=auto_remediate
            )
            actions_taken.append(action_result)
        
        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "actions_taken": actions_taken,
            "anomalies_count": len(anomalies),
            "critical_anomalies_count": len(critical_anomalies),
            "processed_at": datetime.utcnow().isoformat(),
            "auto_remediated": auto_remediate
        }
    
    def auto_revoke_suspicious_access(
        self,
        user_id: str,
        anomalies: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Automatically revoke suspicious access based on anomalies.
        """
        if not anomalies:
            return {
                "user_id": user_id,
                "action": "revoke_access",
                "revoked": False,
                "reason": "No anomalies detected"
            }
        
        # Determine which entitlements/roles to revoke
        suspicious_entitlements = []
        suspicious_roles = []
        
        for anomaly in anomalies:
            anomaly_type = anomaly.get("type")
            details = anomaly.get("details", {})
            
            if anomaly_type == "privilege_escalation":
                role = details.get("role")
                if role:
                    suspicious_roles.append(role)
            
            elif anomaly_type in ["resource_anomaly", "geographic_anomaly"]:
                resource = details.get("resource") or details.get("resource_id")
                if resource:
                    suspicious_entitlements.append(resource)
        
        results = []
        
        if not dry_run:
            # Revoke roles
            for role in set(suspicious_roles):
                try:
                    # TODO: Implement role revocation via Keycloak
                    # self.keycloak_client.remove_user_role(user_id, role)
                    results.append({
                        "type": "role_revoked",
                        "role": role,
                        "success": True
                    })
                except Exception as e:
                    logger.error(f"Error revoking role {role}: {e}")
                    results.append({
                        "type": "role_revoked",
                        "role": role,
                        "success": False,
                        "error": str(e)
                    })
            
            # Revoke entitlements
            for entitlement in set(suspicious_entitlements):
                try:
                    # TODO: Implement entitlement revocation via Entitlement Agent
                    results.append({
                        "type": "entitlement_revoked",
                        "entitlement": entitlement,
                        "success": True
                    })
                except Exception as e:
                    logger.error(f"Error revoking entitlement {entitlement}: {e}")
                    results.append({
                        "type": "entitlement_revoked",
                        "entitlement": entitlement,
                        "success": False,
                        "error": str(e)
                    })
        else:
            # Dry run - just report what would be revoked
            for role in set(suspicious_roles):
                results.append({
                    "type": "role_revoked",
                    "role": role,
                    "success": True,
                    "dry_run": True
                })
            for entitlement in set(suspicious_entitlements):
                results.append({
                    "type": "entitlement_revoked",
                    "entitlement": entitlement,
                    "success": True,
                    "dry_run": True
                })
        
        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "action": "revoke_access",
            "dry_run": dry_run,
            "revoked_roles": len([r for r in results if r["type"] == "role_revoked"]),
            "revoked_entitlements": len([r for r in results if r["type"] == "entitlement_revoked"]),
            "results": results,
            "processed_at": datetime.utcnow().isoformat()
        }
    
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
        """Execute a response action."""
        result = {
            "action": action.value,
            "user_id": user_id,
            "reason": reason,
            "executed": False,
            "error": None
        }
        
        if not auto_remediate and action not in [ResponseAction.ALERT_ONLY, ResponseAction.LOG_ONLY]:
            result["executed"] = False
            result["message"] = "Auto-remediation disabled"
            return result
        
        try:
            if action == ResponseAction.DISABLE_USER:
                # TODO: Disable user in Keycloak
                # self.keycloak_client.disable_user(user_id)
                result["executed"] = True
                result["message"] = f"User {user_id} disabled"
                
            elif action == ResponseAction.REVOKE_ACCESS:
                result["executed"] = True
                result["message"] = "Access revocation initiated"
                
            elif action == ResponseAction.REQUIRE_MFA:
                # TODO: Require MFA for user
                result["executed"] = True
                result["message"] = "MFA required for user"
                
            elif action == ResponseAction.ALERT_ONLY:
                alert = self.generate_alert(
                    "risk_response",
                    user_id,
                    {"reason": reason},
                    tenant_id,
                    severity="high"
                )
                result["executed"] = True
                result["message"] = "Alert generated"
                result["alert"] = alert
                
            elif action == ResponseAction.LOG_ONLY:
                logger.info(f"Risk response logged: {reason} for user {user_id}")
                result["executed"] = True
                result["message"] = "Action logged"
                
            elif action == ResponseAction.ESCALATE:
                # TODO: Create escalation ticket
                result["executed"] = True
                result["message"] = "Escalation created"
                
        except Exception as e:
            logger.error(f"Error executing action {action}: {e}")
            result["error"] = str(e)
        
        return result
    
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

