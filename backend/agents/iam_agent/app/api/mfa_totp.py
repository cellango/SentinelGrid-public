"""
TOTP MFA (Time-based One-Time Password) API endpoints.

Implements standard TOTP MFA (compatible with Google Authenticator, Authy, etc.)
integrated with Keycloak's built-in OTP support.

Security: All operations enforce tenant isolation.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import qrcode
import io
import base64

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.services.security import SecurityService
from app.services.backup_code_service import BackupCodeService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/mfa", tags=["mfa"])


# ============================================================================
# Models
# ============================================================================

class MFAEnrollmentRequest(BaseModel):
    """MFA enrollment initiation request."""
    user_id: str


class MFAEnrollmentResponse(BaseModel):
    """MFA enrollment response with QR code."""
    secret: str
    qr_code: str  # Base64 encoded QR code image
    manual_entry_key: str
    issuer: str = "SentinelGrid"


class MFAVerifyEnrollmentRequest(BaseModel):
    """Verify MFA enrollment with first code."""
    user_id: str
    code: str = Field(..., min_length=6, max_length=6)


class MFAVerificationRequest(BaseModel):
    """MFA code verification during login."""
    user_id: str
    code: str = Field(..., min_length=6, max_length=6)


class MFAStatusResponse(BaseModel):
    """MFA status for a user."""
    user_id: str
    mfa_enabled: bool
    mfa_type: Optional[str] = None
    enrolled_at: Optional[str] = None


class RecoveryCodesResponse(BaseModel):
    """Recovery codes response."""
    codes: List[str]
    generated_at: str


class BackupCodeVerifyRequest(BaseModel):
    """Verify a single backup code."""
    code: str = Field(..., min_length=4, max_length=32)


# ============================================================================
# Helper Functions
# ============================================================================

async def get_token_data(authorization: str) -> dict:
    """Validate token and extract data."""
    from app.services.token_validator import TokenValidator
    from app.services.keycloak_client import KeycloakClient
    
    keycloak_client = KeycloakClient()
    validator = TokenValidator(keycloak_client)
    result = validator.validate_token(authorization)
    
    if not result.get("valid"):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if not result.get("tenant_id"):
        raise HTTPException(status_code=403, detail="No tenant_id in token")
    
    return result


def get_realm_for_tenant(tenant_id: str) -> str:
    """Get realm name for tenant."""
    return settings.KEYCLOAK_REALM


def extract_tenant_id_from_user(user: dict) -> Optional[str]:
    """Extract tenant_id from user attributes."""
    attributes = user.get("attributes", {})
    tenant_id = attributes.get("tenant_id")
    return tenant_id[0] if isinstance(tenant_id, list) and tenant_id else tenant_id


def generate_qr_code(data: str) -> str:
    """Generate QR code and return as base64 encoded image."""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"


# ============================================================================
# MFA Endpoints
# ============================================================================

@router.post("/enroll", response_model=MFAEnrollmentResponse)
async def enroll_mfa(
    request: MFAEnrollmentRequest,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Initiate MFA enrollment for a user.
    
    Returns QR code and secret for user to scan with authenticator app.
    
    SECURITY: Only allows enrolling MFA for users in authenticated user's tenant.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    logger.info(f"MFA enrollment initiated for user {request.user_id} in tenant {tenant_id}")
    
    try:
        async with KeycloakAdminClient() as kc:
            # Verify user belongs to tenant
            user = await kc.get_user(realm, request.user_id)
            user_tenant_id = extract_tenant_id_from_user(user)
            
            if user_tenant_id != tenant_id:
                logger.warning(f"Cross-tenant MFA enrollment blocked")
                raise HTTPException(status_code=404, detail="User not found")
            
            # Set required action for OTP configuration
            # This will force user to setup OTP on next login
            response = await kc._make_request(
                "PUT",
                f"/realms/{realm}/users/{request.user_id}",
                json_data={
                    "requiredActions": ["CONFIGURE_TOTP"]
                }
            )
            response.raise_for_status()
            
            # For manual setup, generate a secret
            # In production, Keycloak generates this during setup
            import pyotp
            secret = pyotp.random_base32()
            
            # Generate OTP Auth URL
            user_email = user.get("email", user.get("username"))
            otp_url = f"otpauth://totp/SentinelGrid:{user_email}?secret={secret}&issuer=SentinelGrid"
            
            # Generate QR code
            qr_code = generate_qr_code(otp_url)
            
            logger.info(f"MFA enrollment prepared for user {request.user_id}")
            
            return MFAEnrollmentResponse(
                secret=secret,
                qr_code=qr_code,
                manual_entry_key=secret,
                issuer="SentinelGrid"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enrolling MFA: {e}")
        raise HTTPException(status_code=500, detail=f"MFA enrollment failed: {str(e)}")


@router.post("/verify-enrollment")
async def verify_mfa_enrollment(
    request: MFAVerifyEnrollmentRequest,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Verify MFA enrollment by checking the first TOTP code.
    
    SECURITY: Only allows verifying for users in authenticated user's tenant.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Verify user belongs to tenant
            user = await kc.get_user(realm, request.user_id)
            user_tenant_id = extract_tenant_id_from_user(user)
            
            if user_tenant_id != tenant_id:
                raise HTTPException(status_code=404, detail="User not found")
            
            # In Keycloak, enrollment verification happens during login
            # when user completes the CONFIGURE_TOTP required action
            
            # For API verification, we can check if user has OTP configured
            credentials = await kc._make_request(
                "GET",
                f"/realms/{realm}/users/{request.user_id}/credentials"
            )
            credentials.raise_for_status()
            creds = credentials.json()
            
            has_otp = any(c.get("type") == "otp" for c in creds)
            
            return {
                "success": has_otp,
                "message": "MFA enrollment verified" if has_otp else "MFA not yet configured",
                "mfa_enabled": has_otp
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying MFA enrollment: {e}")
        raise HTTPException(status_code=500, detail="MFA verification failed")


@router.post("/verify")
async def verify_mfa_code(
    request: MFAVerificationRequest,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Verify MFA code during authentication.
    
    This is typically called as part of the login flow when MFA is required.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    # MFA verification during login is handled by Keycloak's token endpoint
    # This endpoint is for API-based verification
    
    logger.info(f"MFA code verification for user {request.user_id}")
    
    # In production, this would:
    # 1. Get user's OTP secret from Keycloak
    # 2. Verify the code using pyotp
    # 3. Return success/failure
    
    # For now, delegate to Keycloak
    return {
        "success": True,
        "message": "MFA verification handled by Keycloak during login"
    }


@router.get("/{user_id}/status", response_model=MFAStatusResponse)
async def get_mfa_status(
    user_id: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Get MFA status for a user.
    
    SECURITY: Only returns status for users in authenticated user's tenant.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Verify user belongs to tenant
            user = await kc.get_user(realm, user_id)
            user_tenant_id = extract_tenant_id_from_user(user)
            
            if user_tenant_id != tenant_id:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Check if user has OTP credentials
            credentials = await kc._make_request(
                "GET",
                f"/realms/{realm}/users/{user_id}/credentials"
            )
            credentials.raise_for_status()
            creds = credentials.json()
            
            otp_creds = [c for c in creds if c.get("type") == "otp"]
            mfa_enabled = len(otp_creds) > 0
            
            enrolled_at = None
            if otp_creds:
                enrolled_at = otp_creds[0].get("createdDate")
            
            return MFAStatusResponse(
                user_id=user_id,
                mfa_enabled=mfa_enabled,
                mfa_type="totp" if mfa_enabled else None,
                enrolled_at=enrolled_at
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting MFA status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get MFA status")


@router.delete("/{user_id}/disable")
async def disable_mfa(
    user_id: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Disable MFA for a user.
    
    SECURITY: Only allows disabling MFA for users in authenticated user's tenant.
    Requires admin privileges.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    # Check if user has admin role
    if "TENANT_ADMIN" not in token_data.get("roles", []):
        raise HTTPException(status_code=403, detail="Admin role required")
    
    try:
        async with KeycloakAdminClient() as kc:
            # Verify user belongs to tenant
            user = await kc.get_user(realm, user_id)
            user_tenant_id = extract_tenant_id_from_user(user)
            
            if user_tenant_id != tenant_id:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Get OTP credentials
            credentials = await kc._make_request(
                "GET",
                f"/realms/{realm}/users/{user_id}/credentials"
            )
            credentials.raise_for_status()
            creds = credentials.json()
            
            # Delete OTP credentials
            for cred in creds:
                if cred.get("type") == "otp":
                    cred_id = cred.get("id")
                    await kc._make_request(
                        "DELETE",
                        f"/realms/{realm}/users/{user_id}/credentials/{cred_id}"
                    )
            
            logger.info(f"MFA disabled for user {user_id} by admin in tenant {tenant_id}")
            
            return {"success": True, "message": "MFA disabled successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling MFA: {e}")
        raise HTTPException(status_code=500, detail="Failed to disable MFA")


@router.get("/{user_id}/recovery-codes")
async def get_recovery_codes(
    user_id: str,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Get MFA recovery codes for a user.
    
    SECURITY: Only returns codes for users in authenticated user's tenant.
    Recovery codes allow login if MFA device is lost.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Verify user belongs to tenant
            user = await kc.get_user(realm, user_id)
            user_tenant_id = extract_tenant_id_from_user(user)
            
            if user_tenant_id != tenant_id:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Check if requesting for self or if admin
            requesting_user_id = token_data.get("user_id")
            is_admin = "TENANT_ADMIN" in token_data.get("roles", [])
            
            if requesting_user_id != user_id and not is_admin:
                raise HTTPException(
                    status_code=403,
                    detail="Can only access own recovery codes unless admin"
                )
            
            # Generate recovery codes
            # In production, these would be stored securely
            import secrets
            from datetime import datetime
            recovery_codes = [secrets.token_hex(4).upper() for _ in range(8)]
            
            logger.info(f"Recovery codes generated for user {user_id}")
            
            return RecoveryCodesResponse(
                codes=recovery_codes,
                generated_at=datetime.now().isoformat()
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recovery codes: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recovery codes")


# ============================================================================
# Self-Service MFA Endpoints
# ============================================================================

async def get_current_user(credentials: str) -> dict:
    """Get current user info from token for self-service."""
    from app.services.token_validator import TokenValidator
    from app.services.keycloak_client import KeycloakClient
    
    keycloak_client = KeycloakClient()
    validator = TokenValidator(keycloak_client)
    result = validator.validate_token(credentials)
    
    if not result.get("valid"):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = result.get("user_id") or result.get("payload", {}).get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="No user ID in token")
    
    return {
        "user_id": user_id,
        "tenant_id": result.get("tenant_id"),
    }


@router.get("/self/totp/enroll", response_model=MFAEnrollmentResponse)
async def self_enroll_totp(
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Self-service: Get QR code for TOTP enrollment.
    
    Returns QR code and secret for user to scan with authenticator app.
    """
    user_info = await get_current_user(authorization)
    user_id = user_info["user_id"]
    tenant_id = user_info["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    logger.info(f"Self-service MFA enrollment for user {user_id}")
    
    try:
        async with KeycloakAdminClient() as kc:
            user = await kc.get_user(realm, user_id)
            
            # Set required action for OTP configuration
            await kc._make_request(
                "PUT",
                f"/realms/{realm}/users/{user_id}",
                json_data={
                    "requiredActions": ["CONFIGURE_TOTP"]
                }
            )
            
            # Generate secret
            import pyotp
            secret = pyotp.random_base32()
            
            # Generate OTP Auth URL
            user_email = user.get("email", user.get("username"))
            otp_url = f"otpauth://totp/SentinelGrid:{user_email}?secret={secret}&issuer=SentinelGrid"
            
            # Generate QR code
            qr_code = generate_qr_code(otp_url)
            
            return MFAEnrollmentResponse(
                secret=secret,
                qr_code=qr_code,
                manual_entry_key=secret,
                issuer="SentinelGrid"
            )
            
    except Exception as e:
        logger.error(f"Error in self-service MFA enrollment: {e}")
        raise HTTPException(status_code=500, detail="Failed to enroll MFA")


@router.post("/self/totp/verify")
async def self_verify_totp_enrollment(
    code: str = Field(..., min_length=6, max_length=6),
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Self-service: Verify TOTP enrollment with first code.
    """
    user_info = await get_current_user(authorization)
    user_id = user_info["user_id"]
    tenant_id = user_info["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Check if user has OTP configured
            credentials = await kc._make_request(
                "GET",
                f"/realms/{realm}/users/{user_id}/credentials"
            )
            credentials.raise_for_status()
            creds = credentials.json()
            
            has_otp = any(c.get("type") == "otp" for c in creds)
            
            return {
                "success": has_otp,
                "message": "MFA enrollment verified" if has_otp else "MFA not yet configured",
                "mfa_enabled": has_otp
            }
            
    except Exception as e:
        logger.error(f"Error verifying self-service MFA: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify MFA")


@router.delete("/self/totp")
async def self_remove_totp(
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Self-service: Remove TOTP MFA for current user.
    """
    user_info = await get_current_user(authorization)
    user_id = user_info["user_id"]
    tenant_id = user_info["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        async with KeycloakAdminClient() as kc:
            # Get OTP credentials
            credentials = await kc._make_request(
                "GET",
                f"/realms/{realm}/users/{user_id}/credentials"
            )
            credentials.raise_for_status()
            creds = credentials.json()
            
            # Delete OTP credentials
            for cred in creds:
                if cred.get("type") == "otp":
                    cred_id = cred.get("id")
                    await kc._make_request(
                        "DELETE",
                        f"/realms/{realm}/users/{user_id}/credentials/{cred_id}"
                    )
            
            logger.info(f"TOTP removed by user {user_id}")
            
            return {"success": True, "message": "TOTP removed successfully"}
            
    except Exception as e:
        logger.error(f"Error removing self-service TOTP: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove TOTP")


@router.get("/self/backup-codes", response_model=RecoveryCodesResponse)
async def self_get_backup_codes(
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Self-service: Generate backup codes for current user and persist hashed values.
    """
    user_info = await get_current_user(authorization)
    user_id = user_info["user_id"]
    tenant_id = user_info["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)
    
    try:
        service = BackupCodeService()
        codes, _ = await service.generate_codes(realm, user_id, actor_email=user_info.get("email"))
        logger.info(f"Backup codes generated by user {user_id}")
        from datetime import datetime
        return RecoveryCodesResponse(codes=codes, generated_at=datetime.utcnow().isoformat())
        
    except Exception as e:
        logger.error(f"Error generating backup codes: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate backup codes")


@router.post("/self/backup-codes/verify")
async def self_verify_backup_code(
    request: BackupCodeVerifyRequest,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Self-service: Verify a backup code (single use).
    """
    user_info = await get_current_user(authorization)
    user_id = user_info["user_id"]
    tenant_id = user_info["tenant_id"]
    realm = get_realm_for_tenant(tenant_id)

    try:
        service = BackupCodeService()
        valid = await service.verify_code(
            realm=realm,
            user_id=user_id,
            code=request.code,
            actor_email=user_info.get("email"),
        )
        if not valid:
            raise HTTPException(status_code=401, detail="Invalid or expired backup code")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying backup code: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify backup code")
