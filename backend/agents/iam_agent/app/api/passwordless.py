"""
Passwordless Authentication API endpoints.

Supports magic link and OTP-based passwordless authentication.
"""

import logging
import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.services.magic_link_service import MagicLinkService
from app.services.otp_service import OTPService
from app.services.audit_service import AuditService
from app.services.security import SecurityService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth/passwordless", tags=["passwordless"])


# ============================================================================
# Request/Response Models
# ============================================================================

class MagicLinkRequest(BaseModel):
    """Magic link request."""
    email: EmailStr
    redirect_uri: Optional[str] = None


class MagicLinkResponse(BaseModel):
    """Magic link response."""
    success: bool
    message: str
    expires_in_seconds: int = 900  # 15 minutes


class OTPRequest(BaseModel):
    """OTP request."""
    email: EmailStr


class OTPResponse(BaseModel):
    """OTP response."""
    success: bool
    message: str
    expires_in_seconds: int = 300  # 5 minutes


class VerifyRequest(BaseModel):
    """Verification request."""
    token: str = Field(..., min_length=1)
    code: Optional[str] = Field(None, min_length=6, max_length=6)


class VerifyResponse(BaseModel):
    """Verification response."""
    success: bool
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    message: Optional[str] = None


# ============================================================================
# Passwordless Endpoints
# ============================================================================

@router.post("/magic-link", response_model=MagicLinkResponse)
async def send_magic_link(request: MagicLinkRequest, http_request: Request):
    """
    Send magic link for passwordless authentication.
    
    Generates a secure token and sends it via email.
    User clicks link to authenticate without password.
    """
    logger.info(f"Magic link requested for {request.email}")
    client_info = SecurityService.extract_client_info(http_request)
    
    try:
        magic_link_service = MagicLinkService()
        realm_name, _ = magic_link_service._resolve_realm_and_client(request.email)
        
        # Generate magic link
        result = await magic_link_service.generate_magic_link(
            email=request.email,
            redirect_uri=request.redirect_uri
        )
        
        AuditService.log_auth_event(
            realm_name=realm_name,
            action="passwordless_magic_link_request",
            actor_email=request.email,
            details={"redirect_uri": request.redirect_uri},
            ip_address=client_info.get("ip_address"),
            user_agent=client_info.get("user_agent")
        )

        return MagicLinkResponse(
            success=True,
            message="Magic link sent to your email",
            expires_in_seconds=result["expires_in_seconds"]
        )
        
    except Exception as e:
        logger.error(f"Error sending magic link: {e}", exc_info=True)
        # Don't reveal if user exists or not (security best practice)
        return MagicLinkResponse(
            success=True,
            message="If an account exists, a magic link has been sent",
            expires_in_seconds=900
        )


@router.post("/otp", response_model=OTPResponse)
async def send_otp(request: OTPRequest, http_request: Request):
    """
    Send OTP code for passwordless authentication.
    
    Generates a 6-digit code and sends it via email/SMS.
    User enters code to authenticate without password.
    """
    logger.info(f"OTP requested for {request.email}")
    client_info = SecurityService.extract_client_info(http_request)
    
    try:
        otp_service = OTPService()
        realm_name, _ = otp_service._resolve_realm_and_client(request.email)
        
        # Generate and send OTP
        result = await otp_service.generate_otp(email=request.email)
        
        AuditService.log_auth_event(
            realm_name=realm_name,
            action="passwordless_otp_request",
            actor_email=request.email,
            ip_address=client_info.get("ip_address"),
            user_agent=client_info.get("user_agent"),
        )

        return OTPResponse(
            success=True,
            message="OTP code sent to your email",
            expires_in_seconds=result["expires_in_seconds"]
        )
        
    except Exception as e:
        logger.error(f"Error sending OTP: {e}", exc_info=True)
        # Don't reveal if user exists or not
        return OTPResponse(
            success=True,
            message="If an account exists, an OTP code has been sent",
            expires_in_seconds=300
        )


@router.post("/verify", response_model=VerifyResponse)
async def verify_passwordless(verify_data: VerifyRequest, http_request: Request):
    """
    Verify magic link token or OTP code.
    
    If valid, returns access token and refresh token for authenticated session.
    """
    logger.info("Passwordless verification attempt")
    client_info = SecurityService.extract_client_info(http_request)
    
    try:
        # Check if it's a magic link token or OTP code
        if verify_data.code:
            # OTP verification
            otp_service = OTPService()
            result = await otp_service.verify_otp(
                code=verify_data.code,
                token=verify_data.token,
                client_info=client_info
            )
        else:
            # Magic link verification
            magic_link_service = MagicLinkService()
            result = await magic_link_service.verify_magic_link(
                token=verify_data.token,
                client_info=client_info
            )
        
        if result.get("valid"):
            # Exchange for Keycloak tokens
            # In production, you would:
            # 1. Get user from token/code
            # 2. Generate Keycloak session
            # 3. Return Keycloak tokens
            
            return VerifyResponse(
                success=True,
                access_token=result.get("access_token"),
                refresh_token=result.get("refresh_token"),
                expires_in=result.get("expires_in", 3600),
                message="Authentication successful"
            )
        else:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token/code"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying passwordless auth: {e}", exc_info=True)
        raise HTTPException(
            status_code=401,
            detail="Verification failed"
        )
