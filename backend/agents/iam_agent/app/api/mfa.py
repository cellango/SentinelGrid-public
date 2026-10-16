"""MFA and Biometric Authentication API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional

from app.api.request_context import RequestContext, get_current_request_context
from app.models.mfa import (
    BiometricEnrollmentRequest,
    BiometricEnrollmentResponse,
    BiometricVerificationRequest,
    BiometricVerificationResponse,
    AdaptiveAuthRequest,
    AdaptiveAuthResponse,
    AdaptiveAuthVerifyRequest,
    AdaptiveAuthVerifyResponse,
    BiometricType,
    AuthRiskLevel
)
from app.services.biometric_auth import BiometricAuthService, BiometricType as ServiceBiometricType
from app.services.adaptive_auth import AdaptiveAuthService, AuthRiskLevel as ServiceAuthRiskLevel
from app.services.keycloak_client import KeycloakClient
from app.api.auth import get_keycloak_client

router = APIRouter(prefix="/internal/iam/mfa", tags=["mfa"])


def _resolve_tenant_id(
    request_context: RequestContext,
    requested_tenant_id: Optional[str] = None,
) -> str:
    authenticated_tenant_id = str(request_context.tenant_id)
    if requested_tenant_id is not None and requested_tenant_id != authenticated_tenant_id:
        raise HTTPException(status_code=403, detail="Access denied: Tenant mismatch")
    return authenticated_tenant_id


def get_biometric_service() -> BiometricAuthService:
    """Get biometric auth service instance."""
    return BiometricAuthService()


def get_adaptive_auth_service() -> AdaptiveAuthService:
    """Get adaptive auth service instance."""
    return AdaptiveAuthService()


@router.post("/biometrics/enroll", response_model=BiometricEnrollmentResponse)
async def enroll_biometric(
    request: BiometricEnrollmentRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    biometric_service: BiometricAuthService = Depends(get_biometric_service)
) -> BiometricEnrollmentResponse:
    """Enroll a user for biometric authentication."""
    try:
        biometric_type = ServiceBiometricType(request.biometric_type.value)
        
        result = biometric_service.enroll_biometric(
            user_id=request.user_id,
            biometric_type=biometric_type,
            enrollment_data=request.enrollment_data,
            tenant_id=_resolve_tenant_id(request_context, request.tenant_id)
        )
        
        return BiometricEnrollmentResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enrolling biometric: {str(e)}")


@router.post("/biometrics/verify", response_model=BiometricVerificationResponse)
async def verify_biometric(
    request: BiometricVerificationRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    biometric_service: BiometricAuthService = Depends(get_biometric_service)
) -> BiometricVerificationResponse:
    """Verify biometric authentication."""
    try:
        biometric_type = ServiceBiometricType(request.biometric_type.value)
        
        result = biometric_service.verify_biometric(
            user_id=request.user_id,
            biometric_type=biometric_type,
            verification_data=request.verification_data,
            tenant_id=_resolve_tenant_id(request_context, request.tenant_id)
        )
        
        return BiometricVerificationResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying biometric: {str(e)}")


@router.get("/biometrics/{user_id}")
async def get_user_biometrics(
    user_id: str,
    tenant_id: Optional[str] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
    biometric_service: BiometricAuthService = Depends(get_biometric_service)
) -> Dict[str, Any]:
    """Get all enrolled biometrics for a user."""
    try:
        result = biometric_service.get_user_biometrics(
            user_id,
            _resolve_tenant_id(request_context, tenant_id),
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user biometrics: {str(e)}")


@router.delete("/biometrics/{user_id}/{biometric_type}")
async def delete_biometric_enrollment(
    user_id: str,
    biometric_type: str,
    tenant_id: Optional[str] = Query(None),
    request_context: RequestContext = Depends(get_current_request_context),
    biometric_service: BiometricAuthService = Depends(get_biometric_service)
) -> Dict[str, Any]:
    """Delete a biometric enrollment."""
    try:
        biometric_type_enum = ServiceBiometricType(biometric_type)
        result = biometric_service.delete_biometric_enrollment(
            user_id=user_id,
            biometric_type=biometric_type_enum,
            tenant_id=_resolve_tenant_id(request_context, tenant_id)
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting biometric enrollment: {str(e)}")


@router.post("/adaptive/calculate-risk", response_model=AdaptiveAuthResponse)
async def calculate_auth_risk(
    request: AdaptiveAuthRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    adaptive_service: AdaptiveAuthService = Depends(get_adaptive_auth_service)
) -> AdaptiveAuthResponse:
    """Calculate authentication risk score."""
    try:
        result = adaptive_service.calculate_risk_score(
            user_id=request.user_id,
            auth_context=request.auth_context,
            tenant_id=_resolve_tenant_id(request_context, request.tenant_id)
        )
        
        return AdaptiveAuthResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating risk: {str(e)}")


@router.post("/adaptive/requirements", response_model=AdaptiveAuthResponse)
async def get_auth_requirements(
    request: AdaptiveAuthRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    adaptive_service: AdaptiveAuthService = Depends(get_adaptive_auth_service)
) -> AdaptiveAuthResponse:
    """Get authentication requirements based on risk."""
    try:
        result = adaptive_service.determine_auth_requirements(
            user_id=request.user_id,
            auth_context=request.auth_context,
            tenant_id=_resolve_tenant_id(request_context, request.tenant_id)
        )
        
        return AdaptiveAuthResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error determining requirements: {str(e)}")


@router.post("/adaptive/verify", response_model=AdaptiveAuthVerifyResponse)
async def verify_adaptive_auth(
    request: AdaptiveAuthVerifyRequest,
    request_context: RequestContext = Depends(get_current_request_context),
    adaptive_service: AdaptiveAuthService = Depends(get_adaptive_auth_service)
) -> AdaptiveAuthVerifyResponse:
    """Verify adaptive authentication with provided factors."""
    try:
        result = await adaptive_service.verify_adaptive_auth(
            user_id=request.user_id,
            provided_factors=request.provided_factors,
            auth_context=request.auth_context,
            tenant_id=_resolve_tenant_id(request_context, request.tenant_id)
        )
        
        return AdaptiveAuthVerifyResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying adaptive auth: {str(e)}")
