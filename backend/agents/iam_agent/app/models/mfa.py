"""Models for MFA and biometric authentication."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class BiometricType(str, Enum):
    """Biometric types."""
    KEYSTROKE_DYNAMICS = "keystroke_dynamics"
    MOUSE_DYNAMICS = "mouse_dynamics"
    VOICE_RECOGNITION = "voice_recognition"
    DEVICE_FINGERPRINT = "device_fingerprint"
    FACE_RECOGNITION = "face_recognition"
    FINGERPRINT = "fingerprint"


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


class BiometricEnrollmentRequest(BaseModel):
    """Request to enroll a biometric."""
    user_id: str
    biometric_type: BiometricType
    enrollment_data: Dict[str, Any] = Field(..., description="Biometric-specific enrollment data")
    tenant_id: Optional[str] = None


class BiometricEnrollmentResponse(BaseModel):
    """Response from biometric enrollment."""
    user_id: str
    biometric_type: str
    status: str
    enrolled_at: Optional[datetime] = None
    samples_used: Optional[int] = None
    message: Optional[str] = None


class BiometricVerificationRequest(BaseModel):
    """Request to verify a biometric."""
    user_id: str
    biometric_type: BiometricType
    verification_data: Dict[str, Any] = Field(..., description="Biometric verification data")
    tenant_id: Optional[str] = None


class BiometricVerificationResponse(BaseModel):
    """Response from biometric verification."""
    user_id: str
    biometric_type: str
    verified: bool
    score: Optional[float] = None
    threshold: Optional[float] = None
    confidence: Optional[str] = None
    reason: Optional[str] = None
    verified_at: datetime


class AdaptiveAuthRequest(BaseModel):
    """Request for adaptive authentication."""
    user_id: str
    auth_context: Dict[str, Any] = Field(..., description="Authentication context (device, location, etc.)")
    tenant_id: Optional[str] = None


class AdaptiveAuthResponse(BaseModel):
    """Response from adaptive authentication."""
    user_id: str
    risk_score: float
    risk_level: str
    risk_factors: Dict[str, float]
    required_factors: List[str]
    policies: Dict[str, Any]
    calculated_at: datetime


class AdaptiveAuthVerifyRequest(BaseModel):
    """Request to verify adaptive authentication."""
    user_id: str
    provided_factors: List[Dict[str, Any]] = Field(..., description="List of authentication factors with data")
    auth_context: Dict[str, Any] = Field(..., description="Authentication context")
    tenant_id: Optional[str] = None


class AdaptiveAuthVerifyResponse(BaseModel):
    """Response from adaptive auth verification."""
    verified: bool
    risk_score: float
    risk_level: str
    factor_results: List[Dict[str, Any]]
    required_factors: List[str]
    missing_factors: Optional[List[str]] = None
    verified_at: datetime
