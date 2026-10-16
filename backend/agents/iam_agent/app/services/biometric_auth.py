"""
Biometric Authentication Service
Manages various biometric authentication methods
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

from app.services.keystroke_dynamics import KeystrokeDynamicsService
from app.services.mouse_dynamics import MouseDynamicsService

logger = logging.getLogger(__name__)


class BiometricType(str, Enum):
    """Types of biometric authentication."""
    KEYSTROKE_DYNAMICS = "keystroke_dynamics"
    MOUSE_DYNAMICS = "mouse_dynamics"
    VOICE_RECOGNITION = "voice_recognition"
    DEVICE_FINGERPRINT = "device_fingerprint"
    FACE_RECOGNITION = "face_recognition"
    FINGERPRINT = "fingerprint"


class BiometricAuthService:
    """Service for managing biometric authentication."""
    
    def __init__(self):
        self.keystroke_service = KeystrokeDynamicsService()
        self.mouse_service = MouseDynamicsService()
        self.enabled_biometrics: Dict[str, bool] = {
            BiometricType.KEYSTROKE_DYNAMICS.value: True,
            BiometricType.MOUSE_DYNAMICS.value: True,
            BiometricType.VOICE_RECOGNITION.value: False,  # To be implemented
            BiometricType.DEVICE_FINGERPRINT.value: True,
            BiometricType.FACE_RECOGNITION.value: False,  # To be implemented
            BiometricType.FINGERPRINT.value: False  # To be implemented
        }
    
    def enroll_biometric(
        self,
        user_id: str,
        biometric_type: BiometricType,
        enrollment_data: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enroll a user for biometric authentication.
        
        Args:
            user_id: User ID
            biometric_type: Type of biometric
            enrollment_data: Biometric-specific enrollment data
            tenant_id: Tenant ID for multi-tenancy
            
        Returns:
            Enrollment result
        """
        if not self.enabled_biometrics.get(biometric_type.value, False):
            return {
                "user_id": user_id,
                "biometric_type": biometric_type.value,
                "status": "not_enabled",
                "message": f"Biometric type {biometric_type.value} is not enabled"
            }
        
        try:
            if biometric_type == BiometricType.KEYSTROKE_DYNAMICS:
                keystroke_samples = enrollment_data.get("samples", [])
                result = self.keystroke_service.enroll_user(
                    user_id,
                    keystroke_samples,
                    tenant_id
                )
            
            elif biometric_type == BiometricType.MOUSE_DYNAMICS:
                mouse_samples = enrollment_data.get("samples", [])
                result = self.mouse_service.enroll_user(
                    user_id,
                    mouse_samples,
                    tenant_id
                )
            
            elif biometric_type == BiometricType.DEVICE_FINGERPRINT:
                result = self._enroll_device_fingerprint(
                    user_id,
                    enrollment_data,
                    tenant_id
                )
            
            else:
                result = {
                    "user_id": user_id,
                    "biometric_type": biometric_type.value,
                    "status": "not_implemented",
                    "message": f"Enrollment for {biometric_type.value} not yet implemented"
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error enrolling biometric: {e}")
            return {
                "user_id": user_id,
                "biometric_type": biometric_type.value,
                "status": "error",
                "error": str(e)
            }
    
    def verify_biometric(
        self,
        user_id: str,
        biometric_type: BiometricType,
        verification_data: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify biometric authentication.
        
        Returns:
            Verification result with score and decision
        """
        if not self.enabled_biometrics.get(biometric_type.value, False):
            return {
                "user_id": user_id,
                "biometric_type": biometric_type.value,
                "verified": False,
                "reason": "biometric_not_enabled"
            }
        
        try:
            if biometric_type == BiometricType.KEYSTROKE_DYNAMICS:
                result = self.keystroke_service.verify_keystroke_pattern(
                    user_id,
                    verification_data,
                    tenant_id
                )
            
            elif biometric_type == BiometricType.MOUSE_DYNAMICS:
                result = self.mouse_service.verify_mouse_pattern(
                    user_id,
                    verification_data,
                    tenant_id
                )
            
            elif biometric_type == BiometricType.DEVICE_FINGERPRINT:
                result = self._verify_device_fingerprint(
                    user_id,
                    verification_data,
                    tenant_id
                )
            
            else:
                result = {
                    "user_id": user_id,
                    "biometric_type": biometric_type.value,
                    "verified": False,
                    "reason": "not_implemented"
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error verifying biometric: {e}")
            return {
                "user_id": user_id,
                "biometric_type": biometric_type.value,
                "verified": False,
                "error": str(e)
            }
    
    def get_user_biometrics(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all enrolled biometrics for a user."""
        enrolled_biometrics = {}
        
        # Check each biometric type
        for biometric_type in BiometricType:
            if self._is_user_enrolled(user_id, biometric_type, tenant_id):
                enrolled_biometrics[biometric_type.value] = {
                    "enrolled": True,
                    "enabled": self.enabled_biometrics.get(biometric_type.value, False)
                }
            else:
                enrolled_biometrics[biometric_type.value] = {
                    "enrolled": False,
                    "enabled": self.enabled_biometrics.get(biometric_type.value, False)
                }
        
        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "biometrics": enrolled_biometrics,
            "enrolled_count": sum(1 for b in enrolled_biometrics.values() if b["enrolled"]),
            "total_enabled": sum(1 for enabled in self.enabled_biometrics.values() if enabled)
        }
    
    def delete_biometric_enrollment(
        self,
        user_id: str,
        biometric_type: BiometricType,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Delete a biometric enrollment."""
        # TODO: Implement deletion
        return {
            "user_id": user_id,
            "biometric_type": biometric_type.value,
            "status": "deleted",
            "deleted_at": datetime.utcnow().isoformat()
        }
    
    def _enroll_device_fingerprint(
        self,
        user_id: str,
        enrollment_data: Dict[str, Any],
        tenant_id: Optional[str]
    ) -> Dict[str, Any]:
        """Enroll device fingerprint."""
        device_fingerprint = {
            "user_agent": enrollment_data.get("user_agent"),
            "screen_resolution": enrollment_data.get("screen_resolution"),
            "timezone": enrollment_data.get("timezone"),
            "language": enrollment_data.get("language"),
            "platform": enrollment_data.get("platform"),
            "hardware_concurrency": enrollment_data.get("hardware_concurrency"),
            "device_memory": enrollment_data.get("device_memory"),
            "canvas_fingerprint": enrollment_data.get("canvas_fingerprint"),
            "webgl_fingerprint": enrollment_data.get("webgl_fingerprint"),
            "fonts": enrollment_data.get("fonts", []),
            "plugins": enrollment_data.get("plugins", [])
        }
        
        # TODO: Store in database
        
        return {
            "user_id": user_id,
            "biometric_type": BiometricType.DEVICE_FINGERPRINT.value,
            "status": "enrolled",
            "device_fingerprint": device_fingerprint,
            "enrolled_at": datetime.utcnow().isoformat()
        }
    
    def _verify_device_fingerprint(
        self,
        user_id: str,
        verification_data: Dict[str, Any],
        tenant_id: Optional[str]
    ) -> Dict[str, Any]:
        """Verify device fingerprint."""
        # Get enrolled fingerprint (would fetch from DB)
        enrolled = self._get_device_fingerprint(user_id, tenant_id)
        if not enrolled:
            return {
                "user_id": user_id,
                "verified": False,
                "reason": "not_enrolled"
            }
        
        # Compare fingerprints
        score = self._compare_device_fingerprints(enrolled, verification_data)
        threshold = 0.7  # 70% match required
        verified = score >= threshold
        
        return {
            "user_id": user_id,
            "verified": verified,
            "score": round(score, 4),
            "threshold": threshold,
            "verified_at": datetime.utcnow().isoformat()
        }
    
    def _compare_device_fingerprints(
        self,
        enrolled: Dict[str, Any],
        verification: Dict[str, Any]
    ) -> float:
        """Compare two device fingerprints and return similarity score."""
        matches = 0
        total = 0
        
        # Compare each attribute
        for key in enrolled.keys():
            if key in verification:
                total += 1
                if enrolled[key] == verification[key]:
                    matches += 1
                elif isinstance(enrolled[key], list) and isinstance(verification[key], list):
                    # For lists (fonts, plugins), compare intersection
                    common = set(enrolled[key]) & set(verification[key])
                    if len(enrolled[key]) > 0:
                        match_ratio = len(common) / len(enrolled[key])
                        matches += match_ratio
        
        return matches / total if total > 0 else 0.0
    
    def _get_device_fingerprint(
        self,
        user_id: str,
        tenant_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Get enrolled device fingerprint (would fetch from DB)."""
        # TODO: Fetch from database
        return None
    
    def _is_user_enrolled(
        self,
        user_id: str,
        biometric_type: BiometricType,
        tenant_id: Optional[str]
    ) -> bool:
        """Check if user is enrolled for a biometric type."""
        # TODO: Check database
        return False

