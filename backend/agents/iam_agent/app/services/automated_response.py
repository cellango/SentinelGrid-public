"""
Automated Response Service for IAM.

Legacy response compatibility; provider execution is blocked.
"""

from app.services.itdr_service import block_legacy_response

import logging
from typing import Dict, List, Optional


logger = logging.getLogger(__name__)


class AutomatedResponseService:
    """Compatibility methods for unavailable legacy responses."""
    
    def __init__(self, store=None):
        self.store = store
    
    async def respond_to_anomaly(
        self,
        tenant_id: str,
        anomaly: Dict,
        response_rules: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
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
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    async def _lock_account(
        self,
        tenant_id: str,
        user_id: str,
        realm: str,
        anomaly: Dict
    ) -> Dict:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    async def _force_mfa(
        self,
        tenant_id: str,
        user_id: str,
        realm: str,
        anomaly: Dict
    ) -> Dict:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    async def _send_alert(
        self,
        tenant_id: str,
        user_id: Optional[str],
        anomaly: Dict
    ) -> Dict:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    async def _revoke_sessions(
        self,
        tenant_id: str,
        user_id: str,
        realm: str,
        anomaly: Dict
    ) -> Dict:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()

    def _audit_action(self, tenant_id: str, anomaly_id: Optional[str], action: Dict, anomaly: Dict) -> None:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()


def get_realm_for_tenant(tenant_id: str) -> str:
    """A generic realm cannot establish tenant authority."""
    block_legacy_response()
