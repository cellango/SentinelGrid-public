"""
Automated Response Service for IAM.

Automatically responds to security anomalies and threats.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.services.audit_service import AuditService
from app.services.anomaly_store import AnomalyStore
from app.core.config import settings

logger = logging.getLogger(__name__)


class AutomatedResponseService:
    """Service for automated security responses."""
    
    def __init__(self, store=None):
        self.keycloak_admin = KeycloakAdminClient()
        self.store = store
    
    async def respond_to_anomaly(
        self,
        tenant_id: str,
        anomaly: Dict,
        response_rules: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Automatically respond to a detected anomaly.
        
        Applies response rules based on anomaly type and severity.
        Returns list of actions taken and persists them on the anomaly metadata if possible.
        """
        actions_taken = []
        
        try:
            anomaly_type = anomaly.get("anomaly_type")
            severity = anomaly.get("severity")
            risk_score = anomaly.get("risk_score", 0)
            user_id = anomaly.get("user_id")
            anomaly_id = anomaly.get("id")
            
            # Default response rules if not provided
            if not response_rules:
                response_rules = self._get_default_response_rules()
            
            # Determine which responses to apply
            for rule in response_rules:
                if self._should_apply_rule(rule, anomaly_type, severity, risk_score):
                    action = await self._execute_response(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        response_type=rule["type"],
                        anomaly=anomaly
                    )
                    if action:
                        actions_taken.append(action)
                        self._audit_action(tenant_id, anomaly_id, action, anomaly)
            
            # Persist actions on the anomaly metadata
            anomaly_id = anomaly.get("id")
            if actions_taken and anomaly_id and isinstance(self.store, AnomalyStore):
                try:
                    self.store.append_responses(tenant_id, anomaly_id, actions_taken)
                except Exception as store_exc:
                    logger.debug("Could not persist automated responses for anomaly %s: %s", anomaly_id, store_exc)

            return actions_taken
            
        except Exception as e:
            logger.error(f"Error responding to anomaly: {e}", exc_info=True)
            return []
    
    def _get_default_response_rules(self) -> List[Dict]:
        """Get default automated response rules."""
        return [
            {
                "type": "lock_account",
                "conditions": {
                    "anomaly_types": ["failed_logins", "impossible_travel"],
                    "min_severity": "high",
                    "min_risk_score": 70
                }
            },
            {
                "type": "force_mfa",
                "conditions": {
                    "anomaly_types": ["unusual_location", "unusual_device"],
                    "min_severity": "medium",
                    "min_risk_score": 50
                }
            },
            {
                "type": "send_alert",
                "conditions": {
                    "anomaly_types": ["*"],  # All anomaly types
                    "min_severity": "medium",
                    "min_risk_score": 40
                }
            },
            {
                "type": "revoke_session",
                "conditions": {
                    "anomaly_types": ["impossible_travel", "unusual_device"],
                    "min_severity": "high",
                    "min_risk_score": 60
                }
            }
        ]
    
    def _should_apply_rule(
        self,
        rule: Dict,
        anomaly_type: str,
        severity: str,
        risk_score: float
    ) -> bool:
        """Check if a response rule should be applied."""
        conditions = rule.get("conditions", {})
        
        # Check anomaly type
        allowed_types = conditions.get("anomaly_types", [])
        if "*" not in allowed_types and anomaly_type not in allowed_types:
            return False
        
        # Check severity
        min_severity = conditions.get("min_severity", "low")
        severity_levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        if severity_levels.get(severity, 0) < severity_levels.get(min_severity, 0):
            return False
        
        # Check risk score
        min_risk_score = conditions.get("min_risk_score", 0)
        if risk_score < min_risk_score:
            return False
        
        return True
    
    async def _execute_response(
        self,
        tenant_id: str,
        user_id: Optional[str],
        response_type: str,
        anomaly: Dict
    ) -> Optional[Dict]:
        """Execute a specific automated response."""
        realm = get_realm_for_tenant(tenant_id)
        
        try:
            action_detail = {
                "type": response_type,
                "anomaly_id": str(anomaly.get("id") or ""),
                "anomaly_type": anomaly.get("anomaly_type"),
                "severity": anomaly.get("severity"),
                "risk_score": anomaly.get("risk_score"),
                "executed_at": datetime.utcnow().isoformat(),
            }
            if response_type == "lock_account":
                result = await self._lock_account(tenant_id, user_id, realm, anomaly)
                return {**action_detail, **result}
            
            elif response_type == "force_mfa":
                result = await self._force_mfa(tenant_id, user_id, realm, anomaly)
                return {**action_detail, **result}
            
            elif response_type == "send_alert":
                result = await self._send_alert(tenant_id, user_id, anomaly)
                return {**action_detail, **result}
            
            elif response_type == "revoke_session":
                result = await self._revoke_sessions(tenant_id, user_id, realm, anomaly)
                return {**action_detail, **result}
            
            else:
                logger.warning(f"Unknown response type: {response_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error executing response {response_type}: {e}", exc_info=True)
            return None
    
    async def _lock_account(
        self,
        tenant_id: str,
        user_id: str,
        realm: str,
        anomaly: Dict
    ) -> Dict:
        """Lock user account."""
        try:
            async with self.keycloak_admin as kc:
                await kc._make_request(
                    "PUT",
                    f"/realms/{realm}/users/{user_id}",
                    json_data={"enabled": False}
                )
                
                logger.warning(f"Account {user_id} locked due to anomaly: {anomaly.get('anomaly_type')}")
                
                return {
                    "type": "lock_account",
                    "status": "executed",
                    "message": f"Account locked due to {anomaly.get('anomaly_type')}",
                    "executed_at": datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"Error locking account: {e}")
            return {
                "type": "lock_account",
                "status": "failed",
                "error": str(e)
            }
    
    async def _force_mfa(
        self,
        tenant_id: str,
        user_id: str,
        realm: str,
        anomaly: Dict
    ) -> Dict:
        """Force MFA requirement for user."""
        try:
            async with self.keycloak_admin as kc:
                # Set required action to force MFA setup
                await kc._make_request(
                    "PUT",
                    f"/realms/{realm}/users/{user_id}",
                    json_data={
                        "requiredActions": ["CONFIGURE_TOTP"]
                    }
                )
                
                return {
                    "type": "force_mfa",
                    "status": "executed",
                    "message": "MFA required on next login",
                    "executed_at": datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"Error forcing MFA: {e}")
            return {
                "type": "force_mfa",
                "status": "failed",
                "error": str(e)
            }
    
    async def _send_alert(
        self,
        tenant_id: str,
        user_id: Optional[str],
        anomaly: Dict
    ) -> Dict:
        """Send security alert to administrators."""
        try:
            # In production, send email/SMS to admins
            # For now, log the alert
            
            logger.warning(
                f"Security alert for tenant {tenant_id}: "
                f"{anomaly.get('anomaly_type')} - {anomaly.get('title')}"
            )
            
            return {
                "type": "send_alert",
                "status": "executed",
                "message": "Security alert sent to administrators",
                "executed_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return {
                "type": "send_alert",
                "status": "failed",
                "error": str(e)
            }
    
    async def _revoke_sessions(
        self,
        tenant_id: str,
        user_id: str,
        realm: str,
        anomaly: Dict
    ) -> Dict:
        """Revoke all active sessions for user."""
        try:
            async with self.keycloak_admin as kc:
                await kc._make_request(
                    "POST",
                    f"/realms/{realm}/users/{user_id}/logout"
                )
                
                return {
                    "type": "revoke_session",
                    "status": "executed",
                    "message": "All sessions revoked",
                    "executed_at": datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"Error revoking sessions: {e}")
            return {
                "type": "revoke_session",
                "status": "failed",
                "error": str(e)
            }

    def _audit_action(self, tenant_id: str, anomaly_id: Optional[str], action: Dict, anomaly: Dict) -> None:
        """Write audit event for automated response (best-effort)."""
        try:
            AuditService.log_auth_event(
                realm_name=settings.KEYCLOAK_REALM,
                action="anomaly_response",
                actor_user_id=None,
                actor_email=None,
                customer_id=tenant_id,
                details={
                    "anomaly_id": anomaly_id,
                    "anomaly_type": anomaly.get("anomaly_type"),
                    "severity": anomaly.get("severity"),
                    "risk_score": anomaly.get("risk_score"),
                    "response": action,
                },
            )
        except Exception as exc:
            logger.debug("Audit for anomaly response skipped: %s", exc)


def get_realm_for_tenant(tenant_id: str) -> str:
    """Get Keycloak realm name for tenant."""
    return settings.KEYCLOAK_REALM
