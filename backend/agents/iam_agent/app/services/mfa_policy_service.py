"""
MFA Policy Service for context-aware multi-factor authentication.

Evaluates device trust, IP/geo risk, and time-based policies to determine
when MFA should be required.
"""

import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.core.config import settings

logger = logging.getLogger(__name__)


class MFAPolicyService:
    """Service for evaluating MFA policies."""
    
    def __init__(self):
        self.keycloak_admin = KeycloakAdminClient()
    
    async def evaluate_mfa_requirement(
        self,
        user_id: str,
        tenant_id: str,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        geo_location: Optional[Dict] = None,
        time_of_day: Optional[datetime] = None,
        target_app: Optional[str] = None,
        requested_roles: Optional[List[str]] = None,
    ) -> Dict:
        """
        Evaluate whether MFA should be required for a login attempt.
        
        Returns:
        {
            "mfa_required": bool,
            "reason": str,
            "risk_score": float (0-100),
            "factors": List[str]
        }
        """
        realm = get_realm_for_tenant(tenant_id)
        risk_score = 0.0
        factors = []
        mfa_required = False
        policy_threshold = settings.MFA_RISK_THRESHOLD
        enforced_apps = {app.lower() for app in (settings.MFA_ENFORCED_APPS or [])}
        enforced_roles = {role.lower() for role in (settings.MFA_ENFORCED_ROLES or [])}
        enforced_hit = False
        
        try:
            # Factor 1: Device Trust
            if device_id:
                device_trust = await self._check_device_trust(user_id, device_id, tenant_id)
                if not device_trust.get("trusted"):
                    risk_score += 30.0
                    factors.append("Untrusted device")
                else:
                    risk_score -= 10.0
                    factors.append("Trusted device")
            
            # Factor 2: IP Address
            if ip_address:
                ip_risk = await self._check_ip_risk(user_id, ip_address, tenant_id)
                if ip_risk.get("suspicious"):
                    risk_score += 25.0
                    factors.append("Suspicious IP address")
                elif ip_risk.get("unusual"):
                    risk_score += 15.0
                    factors.append("Unusual IP address")
            
            # Factor 3: Geo-location
            if geo_location:
                geo_risk = await self._check_geo_risk(user_id, geo_location, tenant_id)
                if geo_risk.get("impossible_travel"):
                    risk_score += 40.0
                    factors.append("Impossible travel detected")
                elif geo_risk.get("unusual_location"):
                    risk_score += 20.0
                    factors.append("Unusual location")
            
            # Factor 4: Time of Day
            if time_of_day:
                time_risk = self._check_time_risk(user_id, time_of_day, tenant_id)
                if time_risk.get("unusual_hours"):
                    risk_score += 10.0
                    factors.append("Unusual login time")
            
            # Factor 5: Recent Failed Attempts
            failed_attempts = await self._check_failed_attempts(user_id, tenant_id)
            if failed_attempts > 0:
                risk_score += failed_attempts * 5.0
                factors.append(f"{failed_attempts} recent failed attempts")
            
            # Factor 6: App-level enforcement
            if target_app and target_app.lower() in enforced_apps:
                enforced_hit = True
                factors.append(f"MFA enforced for app {target_app}")
                risk_score = max(risk_score, policy_threshold)

            # Factor 7: Role-level enforcement
            if enforced_roles:
                # Prefer passed-in roles; fall back to lookup
                roles = requested_roles or await self._get_user_roles(realm, user_id)
                role_hits = [
                    role for role in roles or []
                    if role and role.lower() in enforced_roles
                ]
                if role_hits:
                    enforced_hit = True
                    factors.append(f"MFA enforced for roles: {', '.join(role_hits)}")
                    risk_score = max(risk_score, policy_threshold)

            # Determine if MFA required
            mfa_required = enforced_hit or (risk_score >= policy_threshold)
            
            return {
                "mfa_required": mfa_required,
                "reason": ", ".join(factors) if factors else "Standard login",
                "risk_score": min(100.0, max(0.0, risk_score)),
                "factors": factors
            }
            
        except Exception as e:
            logger.error(f"Error evaluating MFA requirement: {e}", exc_info=True)
            # Default to requiring MFA on error (fail secure)
            return {
                "mfa_required": True,
                "reason": "Policy evaluation error",
                "risk_score": 50.0,
                "factors": ["Evaluation error"]
            }
    
    async def _check_device_trust(
        self,
        user_id: str,
        device_id: str,
        tenant_id: str
    ) -> Dict:
        """Check if device is trusted."""
        # In production, query device inventory
        # For now, return placeholder
        return {"trusted": False}
    
    async def _check_ip_risk(
        self,
        user_id: str,
        ip_address: str,
        tenant_id: str
    ) -> Dict:
        """Check if IP address is suspicious or unusual."""
        # In production, check:
        # - Known malicious IPs
        # - User's usual IP addresses
        # - VPN/proxy detection
        
        # Get user's recent login IPs
        # Compare with current IP
        
        return {"suspicious": False, "unusual": False}
    
    async def _check_geo_risk(
        self,
        user_id: str,
        geo_location: Dict,
        tenant_id: str
    ) -> Dict:
        """Check for impossible travel or unusual location."""
        # In production, check:
        # - Last known location
        # - Travel time between locations
        # - Known locations (home, office)
        
        return {"impossible_travel": False, "unusual_location": False}
    
    def _check_time_risk(
        self,
        user_id: str,
        time_of_day: datetime,
        tenant_id: str
    ) -> Dict:
        """Check if login time is unusual."""
        hour = time_of_day.hour
        # Unusual if outside business hours (8 AM - 6 PM)
        unusual_hours = hour < 8 or hour > 18
        
        return {"unusual_hours": unusual_hours}
    
    async def _check_failed_attempts(
        self,
        user_id: str,
        tenant_id: str
    ) -> int:
        """Check recent failed login attempts."""
        # In production, query audit logs for failed logins in last hour
        return 0

    async def _get_user_roles(self, realm: str, user_id: str) -> List[str]:
        """Fetch user realm roles; fail open with empty list."""
        try:
            roles = await self.keycloak_admin.get_user_realm_roles(realm, user_id)
            return [role.get("name") for role in roles if role.get("name")]
        except Exception as exc:
            logger.debug("Role lookup failed for %s in realm %s: %s", user_id, realm, exc)
            return []


def get_realm_for_tenant(tenant_id: str) -> str:
    """Get Keycloak realm name for tenant."""
    return settings.KEYCLOAK_REALM
