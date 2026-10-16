"""
Adaptive Authentication Service
Implements risk-based adaptive authentication using multiple factors
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

from app.core.config import settings
from app.services.backup_code_service import BackupCodeService

logger = logging.getLogger(__name__)


class AuthRiskLevel(str, Enum):
    """Authentication risk levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuthFactor(str, Enum):
    """Authentication factors."""
    PASSWORD = "password"
    TOTP = "totp"
    BACKUP_CODE = "backup_code"
    SMS_OTP = "sms_otp"
    EMAIL_OTP = "email_otp"
    KEYSTROKE_DYNAMICS = "keystroke_dynamics"
    MOUSE_DYNAMICS = "mouse_dynamics"
    DEVICE_FINGERPRINT = "device_fingerprint"
    VOICE_RECOGNITION = "voice_recognition"
    LOCATION = "location"
    TIME_BASED = "time_based"


class AdaptiveAuthService:
    """Service for adaptive/risk-based authentication."""
    
    def __init__(self):
        self.base_auth_factors = [AuthFactor.PASSWORD]
        self.risk_thresholds = {
            AuthRiskLevel.LOW: 0.25,
            AuthRiskLevel.MEDIUM: 0.45,
            AuthRiskLevel.HIGH: 0.6,
            AuthRiskLevel.CRITICAL: 0.8
        }
    
    def calculate_risk_score(
        self,
        user_id: str,
        auth_context: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate authentication risk score based on context.
        
        Risk factors:
        - Device trust/posture
        - Geo/IP reputation (impossible travel, deny/allow lists)
        - Time (unusual time?)
        - Behavior (keystroke/mouse patterns)
        - Previous authentication history (failed logins, recent anomalies)
        """
        risk_factors = {}
        total_risk = 0.0
        
        # 1. Device trust/posture risk
        device_risk = self._assess_device_risk(auth_context)
        risk_factors["device"] = device_risk
        total_risk += device_risk * 0.35
        
        # 2. Location risk
        location_risk = self._assess_location_risk(user_id, auth_context, tenant_id)
        risk_factors["location"] = location_risk
        total_risk += location_risk * 0.35
        
        # 3. Time-based risk
        time_risk = self._assess_time_risk(auth_context)
        risk_factors["time"] = time_risk
        total_risk += time_risk * 0.1
        
        # 4. Behavioral risk (keystroke/mouse patterns)
        behavior_risk = self._assess_behavioral_risk(user_id, auth_context, tenant_id)
        risk_factors["behavior"] = behavior_risk
        total_risk += behavior_risk * 0.1
        
        # 5. Previous authentication risk
        history_risk = self._assess_history_risk(user_id, tenant_id, auth_context)
        risk_factors["history"] = history_risk
        total_risk += history_risk * 0.1
        
        # Normalize to 0-1 range
        total_risk = min(1.0, max(0.0, total_risk))
        
        # Determine risk level
        if total_risk >= self.risk_thresholds[AuthRiskLevel.CRITICAL]:
            risk_level = AuthRiskLevel.CRITICAL
        elif total_risk >= self.risk_thresholds[AuthRiskLevel.HIGH]:
            risk_level = AuthRiskLevel.HIGH
        elif total_risk >= self.risk_thresholds[AuthRiskLevel.MEDIUM]:
            risk_level = AuthRiskLevel.MEDIUM
        else:
            risk_level = AuthRiskLevel.LOW
        
        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "risk_score": round(total_risk, 4),
            "risk_level": risk_level.value,
            "risk_factors": {k: round(v, 4) for k, v in risk_factors.items()},
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    def determine_auth_requirements(
        self,
        user_id: str,
        auth_context: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Determine authentication requirements based on risk score.
        
        Returns:
            Required authentication factors and policies
        """
        risk_result = self.calculate_risk_score(user_id, auth_context, tenant_id)
        risk_level = AuthRiskLevel(risk_result["risk_level"])
        risk_score = risk_result["risk_score"]
        
        # Determine required factors
        required_factors = [AuthFactor.PASSWORD.value]  # Always required
        policies = {
            "session_timeout": self._get_session_timeout(risk_level),
            "require_reauthentication": risk_level in [AuthRiskLevel.HIGH, AuthRiskLevel.CRITICAL],
            "monitor_session": risk_level != AuthRiskLevel.LOW,
            "require_email_verification": risk_level == AuthRiskLevel.CRITICAL,
            "allow_backup_codes": risk_level in [AuthRiskLevel.HIGH, AuthRiskLevel.CRITICAL],
            "step_up_required": risk_level in [AuthRiskLevel.MEDIUM, AuthRiskLevel.HIGH, AuthRiskLevel.CRITICAL],
        }

        if risk_level in [AuthRiskLevel.HIGH, AuthRiskLevel.CRITICAL]:
            required_factors.append(AuthFactor.TOTP.value)

            if risk_level == AuthRiskLevel.CRITICAL:
                # Critical risk - strongly bind to device/behavior
                required_factors.append(AuthFactor.DEVICE_FINGERPRINT.value)
        elif risk_level == AuthRiskLevel.MEDIUM:
            # Medium risk - prefer device binding
            required_factors.append(AuthFactor.DEVICE_FINGERPRINT.value)
        
        return {
            "user_id": user_id,
            "risk_score": risk_score,
            "risk_level": risk_level.value,
            "required_factors": required_factors,
            "policies": policies,
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    async def verify_adaptive_auth(
        self,
        user_id: str,
        provided_factors: List[Dict[str, Any]],
        auth_context: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify adaptive authentication with provided factors.
        
        Args:
            user_id: User ID
            provided_factors: List of authentication factors provided
            auth_context: Authentication context
            tenant_id: Tenant ID
            
        Returns:
            Verification result
        """
        # Determine requirements
        requirements = self.determine_auth_requirements(user_id, auth_context, tenant_id)
        required_factors = set(requirements["required_factors"])
        policies = requirements.get("policies", {})
        
        # Password assumed already verified; focus on step-up factors
        required_check = {f for f in required_factors if f != AuthFactor.PASSWORD.value}

        # Check provided factors
        provided_factor_types = {factor["type"] for factor in provided_factors}

        # Allow backup_code as alternative to TOTP when policy permits
        if (
            AuthFactor.TOTP.value in required_check
            and policies.get("allow_backup_codes")
            and AuthFactor.BACKUP_CODE.value in provided_factor_types
        ):
            provided_factor_types.add(AuthFactor.TOTP.value)
        
        # Verify all required factors are provided
        missing_factors = required_check - provided_factor_types
        if missing_factors:
            return {
                "verified": False,
                "missing_factors": list(missing_factors),
                "required_factors": requirements["required_factors"],
                "provided_factors": list(provided_factor_types)
            }
        
        # Verify each factor
        factor_results = []
        all_verified = True
        backup_service = BackupCodeService()
        
        for factor in provided_factors:
            factor_type = factor.get("type")
            factor_data = factor.get("data", {})
            
            factor_result = await self._verify_factor(
                user_id,
                factor_type,
                factor_data,
                tenant_id,
                backup_service=backup_service,
                auth_context=auth_context
            )
            
            factor_results.append({
                "type": factor_type,
                "verified": factor_result.get("verified", False),
                "score": factor_result.get("score")
            })
            
            if not factor_result.get("verified", False):
                all_verified = False
        
        return {
            "verified": all_verified,
            "risk_score": requirements["risk_score"],
            "risk_level": requirements["risk_level"],
            "factor_results": factor_results,
            "required_factors": requirements["required_factors"],
            "verified_at": datetime.utcnow().isoformat()
        }
    
    def _assess_device_risk(self, auth_context: Dict[str, Any]) -> float:
        """Assess risk based on device trust."""
        device_trusted = auth_context.get("device_trusted", False)
        new_device = auth_context.get("new_device", False)
        device_posture = (auth_context.get("device_posture") or "").lower()
        device_fingerprint = auth_context.get("device_fingerprint")

        if device_trusted and device_posture not in {"noncompliant", "untrusted"}:
            return 0.05  # Low risk from trusted and compliant device

        risk = 0.25
        if new_device or not device_fingerprint:
            risk += 0.15

        if device_posture in {"noncompliant", "untrusted"}:
            risk += 0.25
        elif device_posture == "unknown":
            risk += 0.1

        return min(0.9, risk)
    
    def _assess_location_risk(
        self,
        user_id: str,
        auth_context: Dict[str, Any],
        tenant_id: Optional[str]
    ) -> float:
        """Assess risk based on location."""
        current_location = auth_context.get("location")
        current_ip = auth_context.get("ip_address")
        ip_reputation = (auth_context.get("ip_reputation") or "").lower()
        impossible_travel = auth_context.get("impossible_travel", False)
        geo_anomaly = auth_context.get("geo_anomaly", False)
        deny_country = auth_context.get("deny_country", False)

        # Baseline if no data
        if not current_location and not current_ip and not ip_reputation:
            return 0.2

        risk = 0.25
        if impossible_travel:
            risk += 0.6
        if geo_anomaly or deny_country:
            risk += 0.25

        if ip_reputation == "high":
            risk += 0.35
        elif ip_reputation == "medium":
            risk += 0.2
        elif ip_reputation == "low":
            risk -= 0.1

        return min(1.0, max(0.0, risk))
    
    def _assess_time_risk(self, auth_context: Dict[str, Any]) -> float:
        """Assess risk based on time of access."""
        current_time = datetime.utcnow()
        hour = current_time.hour
        
        # Business hours (9 AM - 5 PM UTC)
        if 9 <= hour < 17:
            return 0.1  # Low risk during business hours
        elif 6 <= hour < 22:
            return 0.3  # Medium risk during off-hours but reasonable
        else:
            return 0.5  # Higher risk during unusual hours
    
    def _assess_behavioral_risk(
        self,
        user_id: str,
        auth_context: Dict[str, Any],
        tenant_id: Optional[str]
    ) -> float:
        """Assess risk based on behavioral biometrics."""
        keystroke_data = auth_context.get("keystroke_data")
        mouse_data = auth_context.get("mouse_data")
        
        if keystroke_data:
            # TODO: Verify keystroke pattern
            # For now, assume moderate risk if pattern doesn't match
            return 0.3
        
        if mouse_data:
            # TODO: Verify mouse dynamics
            return 0.3
        
        # No behavioral data - moderate risk
        return 0.4
    
    def _assess_history_risk(
        self,
        user_id: str,
        tenant_id: Optional[str],
        auth_context: Dict[str, Any]
    ) -> float:
        """Assess risk based on authentication history."""
        recent_failed = auth_context.get("recent_failed_logins", 0)
        anomaly_flags = auth_context.get("anomaly_flags") or []
        if isinstance(anomaly_flags, dict):
            anomaly_flags = [k for k, v in anomaly_flags.items() if v]

        risk = 0.1
        risk += min(0.5, 0.1 * int(recent_failed))

        if anomaly_flags:
            risk += 0.2

        return min(1.0, risk)
    
    def _get_session_timeout(self, risk_level: AuthRiskLevel) -> int:
        """Get session timeout in minutes based on risk level."""
        timeouts = {
            AuthRiskLevel.LOW: 480,  # 8 hours
            AuthRiskLevel.MEDIUM: 240,  # 4 hours
            AuthRiskLevel.HIGH: 60,  # 1 hour
            AuthRiskLevel.CRITICAL: 15  # 15 minutes
        }
        return timeouts.get(risk_level, 240)
    
    async def _verify_factor(
        self,
        user_id: str,
        factor_type: str,
        factor_data: Dict[str, Any],
        tenant_id: Optional[str],
        backup_service: Optional[BackupCodeService] = None,
        auth_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Verify a single authentication factor."""
        auth_context = auth_context or {}

        if factor_type == AuthFactor.BACKUP_CODE.value and backup_service:
            code = factor_data.get("code")
            if not code:
                return {"verified": False, "score": 0.0}

            # Resolve realm (demo vs default) using context hint or tenant
            realm = auth_context.get("realm") or settings.KEYCLOAK_REALM
            if auth_context.get("email", "").endswith("@demo.sentinelgrid.ai") or auth_context.get("realm") == "demo":
                realm = "demo"

            try:
                verified = await backup_service.verify_code(
                    realm=realm,
                    user_id=user_id,
                    code=code,
                    actor_email=auth_context.get("email"),
                )
            except Exception as exc:
                logger.error(f"Backup code verification error: {exc}", exc_info=True)
                verified = False

            return {"verified": verified, "score": 1.0 if verified else 0.0}

        # TODO: Implement actual factor verification (TOTP, device, biometrics)
        return {
            "verified": True,
            "score": 1.0
        }
