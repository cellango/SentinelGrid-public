"""Authentication API endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from app.models.auth import (
    TokenValidationRequest,
    TokenValidationResponse,
    TokenIntrospectionRequest,
    TokenIntrospectionResponse
)
from app.services.keycloak_client import KeycloakClient
from app.services.keycloak_admin_client import KeycloakAdminClient
from app.services.token_validator import TokenValidator
from pydantic import BaseModel, Field

router = APIRouter(prefix="/internal/iam/auth", tags=["authentication"])

# Initialize services (in production, use dependency injection)
_keycloak_client: KeycloakClient = None
_token_validator: TokenValidator = None


def get_keycloak_client() -> KeycloakClient:
    """Get or create Keycloak client instance."""
    global _keycloak_client
    # Always create a new instance to pick up environment variable changes
    # In production, we might want to cache this with proper invalidation
    _keycloak_client = KeycloakClient()
    return _keycloak_client


def get_token_validator() -> TokenValidator:
    """Get or create token validator instance."""
    global _token_validator
    # Always create a new instance to ensure fresh code (for development)
    # In production, we might want to cache this
    # JWKS verification requires no administrator client or admin-token exchange.
    _token_validator = TokenValidator(None)
    return _token_validator


@router.post("/validate-token", response_model=TokenValidationResponse)
async def validate_token(
    request: TokenValidationRequest,
    validator: TokenValidator = Depends(get_token_validator)
) -> TokenValidationResponse:
    """
    Validate a JWT token.
    
    This endpoint validates the token signature, expiration, and claims.
    Returns tenant_id, user_id, roles, and other token claims.
    """
    if not request.token:
        raise HTTPException(status_code=400, detail="Token is required")
    
    result = validator.validate_token(request.token)
    
    return TokenValidationResponse(
        valid=result["valid"],
        payload=result.get("payload"),
        tenant_id=result.get("tenant_id"),
        plan_tier=result.get("plan_tier"),
        user_id=result.get("user_id"),
        username=result.get("username"),
        email=result.get("email"),
        roles=result.get("roles", []),
        error=result.get("error"),
        expires_at=result.get("expires_at")
    )


@router.post("/introspect", response_model=TokenIntrospectionResponse)
async def introspect_token(
    request: TokenIntrospectionRequest,
    validator: TokenValidator = Depends(get_token_validator)
) -> TokenIntrospectionResponse:
    """
    Introspect a token using Keycloak introspection endpoint.
    
    Falls back to JWT validation if introspection is not available.
    """
    if not request.token:
        raise HTTPException(status_code=400, detail="Token is required")
    
    result = validator.introspect_token(request.token)
    
    return TokenIntrospectionResponse(
        active=result.get("active", False),
        sub=result.get("sub"),
        tenant_id=result.get("tenant_id"),
        username=result.get("username"),
        email=result.get("email"),
        realm_access=result.get("realm_access"),
        roles=result.get("roles", []),
        exp=result.get("exp"),
        iat=result.get("iat"),
        error=result.get("error")
    )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    keycloak_client = get_keycloak_client()
    
    # Try to get JWKS URL as connectivity test
    jwks_url = keycloak_client.get_public_key()
    
    return {
        "status": "healthy",
        "service": "iam-agent",
        "keycloak_connected": jwks_url is not None,
        "keycloak_url": keycloak_client.server_url,
        "realm": keycloak_client.realm
    }



# ============================================================================
# PUBLIC AUTH ENDPOINTS - Frontend authentication (login, signup, etc.)
# ============================================================================
"""
Custom authentication API endpoints (no Keycloak redirect).
Implements Direct Access Grant (ROPC) flow for custom login UI.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import httpx
import uuid
import logging
from datetime import datetime

from app.core.config import settings
from app.services.keycloak_admin_client import KeycloakAdminClient
from app.services.keycloak_client import KeycloakClient
from app.services.realm_manager import RealmManager
from app.services.security import SecurityService
from app.services.pricing_service import PricingService
from app.services.audit_service import AuditService
from app.services.mfa_policy_service import MFAPolicyService
from app.utils.slack_notify import notify_slack
import os

logger = logging.getLogger(__name__)

public_router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


def _extract_realm_name(issuer: Optional[str]) -> str:
    """Extract a realm name from an issuer URL."""
    if issuer and "/realms/" in issuer:
        return issuer.split("/realms/")[-1]
    return settings.KEYCLOAK_REALM


def _require_validated_token(
    token: str,
    *,
    error_detail: str = "Invalid token",
    status_code: int = 401,
) -> Dict[str, Any]:
    """Validate a JWT and return the normalized validation payload."""
    validation = TokenValidator(KeycloakClient()).validate_token(token)
    if not validation.get("valid") or not validation.get("payload"):
        logger.warning("Rejected token in public auth path")
        raise HTTPException(status_code=status_code, detail=error_detail)
    return validation


class LoginRequest(BaseModel):
    """Login request model."""
    email: str
    password: str
    remember_me: bool = False
    app_id: Optional[str] = None  # Optional target app for per-app MFA
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v or '.' not in v.split('@')[1]:
            raise ValueError('Invalid email format')
        return v.lower().strip()
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 1:
            raise ValueError('Password is required')
        return v


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
    user: dict
    signup_completed: bool = True  # Default to True for backward compatibility
    password_reset_required: bool = False  # Indicates if password reset is required


class LoginMFARequest(BaseModel):
    """Login with password + OTP for MFA challenge."""
    email: str
    password: str
    otp: str = Field(..., min_length=6, max_length=8)
    remember_me: bool = False


class SignupRequest(BaseModel):
    """Signup request model."""
    company_name: str
    email: str
    password: str
    first_name: str
    last_name: str
    employee_count: int  # Number of employees in the company
    compliance_required: bool = False  # Whether compliance requires dedicated infrastructure
    pricing_tier: Optional[str] = None  # Optional - will be auto-determined from employee_count if not provided
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v or '.' not in v.split('@')[1]:
            raise ValueError('Invalid email format')
        return v.lower().strip()
    
    @validator('password')
    def validate_password(cls, v):
        is_valid, error = SecurityService.validate_password_strength(v)
        if not is_valid:
            raise ValueError(error)
        return v
    
    @validator('company_name')
    def validate_company_name(cls, v):
        v = SecurityService.sanitize_input(v)
        if len(v) < 2:
            raise ValueError('Company name must be at least 2 characters')
        return v
    
    @validator('first_name')
    def validate_first_name(cls, v):
        v = SecurityService.sanitize_input(v).strip()
        if len(v) < 1:
            raise ValueError('First name is required')
        return v
    
    @validator('last_name')
    def validate_last_name(cls, v):
        v = SecurityService.sanitize_input(v).strip()
        if len(v) < 1:
            raise ValueError('Last name is required')
        return v
    
    @validator('employee_count')
    def validate_employee_count(cls, v):
        if v < 1:
            raise ValueError('Employee count must be at least 1')
        if v > 100000:  # Reasonable upper limit
            raise ValueError('Employee count seems too large. Please contact sales for enterprise pricing.')
        return v


class SignupResponse(BaseModel):
    """Signup response model."""
    success: bool
    tenant_id: str
    realm: str
    user_id: str
    message: str


def _detect_realm_from_email(email: str) -> str:
    """Infer realm from email domain with sensible defaults."""
    if email.endswith("@demo.sentinelgrid.ai"):
        return "demo"
    if email.endswith("@sentinelgrid.ai"):
        return settings.KEYCLOAK_REALM
    return settings.KEYCLOAK_REALM


async def _direct_login(email: str, password: str, client_info: dict, otp: str | None = None):
    """
    Shared ROPC login with optional OTP (totp) parameter.
    Raises HTTPException on failures; returns (token_data, realm_name, signup_completed, user_info)
    """
    # Detect realm from email domain or use default
    realm_name = _detect_realm_from_email(email)
    if realm_name == "demo":
        logger.info(f"Detected demo realm from email domain for {SecurityService.mask_sensitive_data(email)}")

    logger.info(f"Attempting login for {SecurityService.mask_sensitive_data(email)} in realm: {realm_name}")

    # Determine client ID based on realm
    client_id = "demo-web" if realm_name == "demo" else "sentinelgrid-web"

    # Authenticate with Keycloak using ROPC flow
    keycloak_url = settings.KEYCLOAK_URL
    token_url = f"{keycloak_url}/realms/{realm_name}/protocol/openid-connect/token"
    logger.debug(f"Token URL: {token_url}")
    logger.debug(f"Client ID: {client_id}")

    try:
        async with httpx.AsyncClient(timeout=10.0, verify=settings.KEYCLOAK_VERIFY_TLS) as client:
            data = {
                "grant_type": "password",
                "client_id": client_id,
                "username": email,
                "password": password,
            }
            if otp:
                data["totp"] = otp
            response = await client.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except Exception as exc:
        await notify_slack(
            "Keycloak auth unreachable",
            {
                "service": "iam_agent",
                "path": "/api/v1/auth/login",
                "user": SecurityService.mask_sensitive_data(email),
                "realm": realm_name,
                "error": str(exc),
            },
        )
        raise HTTPException(
            status_code=500,
            detail="We’ve notified the admin. Try again in a few minutes."
        )

    logger.debug(f"Keycloak response status: {response.status_code}")
    if response.status_code != 200:
        logger.debug(f"Keycloak response body: {response.text[:500]}")

        try:
            error_data = response.json()
        except Exception:
            error_data = {}

        error = error_data.get("error", "authentication_failed")
        error_description = error_data.get("error_description", "").lower()
        error_text = response.text.lower() if response.text else ""

        logger.info(f"🔍 Login failed for {SecurityService.mask_sensitive_data(email)}: error={error}, description={error_description[:200]}")

        password_reset_required = (
            "account is not fully set up" in error_description
            or "account is not fully set up" in error_text
            or "required action" in error_description
            or "required action" in error_text
            or "update password" in error_description
            or "update password" in error_text
            or "temporary password" in error_description
            or "temporary password" in error_text
            or (error == "invalid_grant" and ("account" in error_description or "account" in error_text))
        )

        logger.info(f"🔑 Password reset required check: {password_reset_required} (error={error}, description contains account/required-action)")

        logger.warning(f"Login failed for {SecurityService.mask_sensitive_data(email)}: {error}", extra=client_info)

        AuditService.log_auth_event(
            realm_name=realm_name,
            action="user_login_failed",
            actor_email=email,
            details={"error": error, "password_reset_required": password_reset_required},
            ip_address=client_info.get("ip_address"),
            user_agent=client_info.get("user_agent")
        )

        await notify_slack(
            "Keycloak auth error",
            {
                "service": "iam_agent",
                "path": "/api/v1/auth/login",
                "user": SecurityService.mask_sensitive_data(email),
                "realm": realm_name,
                "status": response.status_code,
                "error": error,
                "error_description": error_description[:200],
            },
        )

        # Map common auth failures to 401 instead of 500
        if error in {"invalid_grant", "invalid_client", "user_not_found", "invalid_user_credentials"}:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        if password_reset_required:
            raise HTTPException(
                status_code=403,
                detail="password_reset_required",
                headers={
                    "X-Password-Reset-Required": "true"
                }
            )

        # If Keycloak signals MFA needed, bubble up cleanly
        if error == "invalid_grant" and "mfa" in error_description:
            raise HTTPException(status_code=412, detail={"error": "mfa_required"})

        raise HTTPException(
            status_code=500,
            detail="We’ve notified the admin. Try again in a few minutes."
        )

    try:
        token_data = response.json()
    except Exception as exc:
        logger.error(f"Unable to parse token response: {exc}")
        raise HTTPException(
            status_code=500,
            detail="We’ve notified the admin. Try again in a few minutes."
        )

    # Validate and normalize claims from the returned access token before using them.
    validation = _require_validated_token(
        token_data["access_token"],
        error_detail="Invalid token returned by identity provider",
        status_code=500,
    )
    payload = validation["payload"]
    user_info = {
        "id": validation.get("user_id"),
        "email": validation.get("email") or email,
        "tenant_id": validation.get("tenant_id"),
        "roles": validation.get("roles", []),
    }
    plan_tier: Optional[str] = validation.get("plan_tier")

    # Normalize tenant_id if missing or mismatched with realm
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        resolved_tenant_id = user_info.get("tenant_id")
        if settings.DB_URL:
            engine = create_engine(settings.DB_URL)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            db = SessionLocal()
            try:
                fallback_slug = None
                if realm_name == "demo" or email.endswith("@demo.sentinelgrid.ai"):
                    fallback_slug = "demo"
                elif realm_name in ("sentinelgrid", "sg-admin"):
                    fallback_slug = "sentinelgrid"

                if fallback_slug:
                    tenant_row = db.execute(
                        text("SELECT id, plan_tier FROM tenants WHERE slug = :slug LIMIT 1"),
                        {"slug": fallback_slug}
                    ).fetchone()
                    if tenant_row:
                        resolved_tenant_id = str(tenant_row[0])
                        plan_tier = tenant_row[1]
                        if user_info.get("tenant_id") != resolved_tenant_id:
                            logger.warning(
                                f"Overriding tenant_id from token ({user_info.get('tenant_id')}) with {resolved_tenant_id} for realm {realm_name}"
                            )
                        user_info["tenant_id"] = resolved_tenant_id
            finally:
                db.close()
    except Exception as e:
        logger.warning(f"Could not normalize tenant_id for {email}: {e}")

    # Check signup completion status from database
    signup_completed = True  # Default to True for backward compatibility
    tenant_id = user_info.get("tenant_id")
    if tenant_id:
        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.orm import sessionmaker

            if settings.DB_URL:
                engine = create_engine(settings.DB_URL)
                SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
                db = SessionLocal()
                try:
                    # Get customer_id from tenant
                    tenant_result = db.execute(
                        text("SELECT customer_id, plan_tier FROM tenants WHERE id = :tenant_id"),
                        {"tenant_id": tenant_id}
                    ).fetchone()

                    if tenant_result:
                        customer_id = tenant_result[0]
                        plan_tier = plan_tier or tenant_result[1]
                        # Check signup_completed status
                        customer_result = db.execute(
                            text("SELECT signup_completed FROM customers WHERE id = :customer_id"),
                            {"customer_id": customer_id}
                        ).fetchone()

                        if customer_result:
                            signup_completed = customer_result[0] if customer_result[0] is not None else True
                except Exception as e:
                    logger.warning(f"Could not check signup_completed status: {e}")
                finally:
                    db.close()
        except Exception as e:
            logger.warning(f"Error checking signup completion: {e}")

    if plan_tier:
        user_info["plan_tier"] = plan_tier

    return token_data, realm_name, signup_completed, user_info


@public_router.post("/login")
async def login(
    request: LoginRequest,
    http_request: Request
):
    """
    Authenticate user with Keycloak (Direct Access Grant / ROPC).
    Applies adaptive MFA risk check; if MFA required, returns 412 with factors.
    """
    client_info = SecurityService.extract_client_info(http_request)
    email = SecurityService.sanitize_input(request.email)

    if not SecurityService.is_safe_email(email):
        logger.warning(f"Unsafe email pattern detected: {email}", extra=client_info)
        raise HTTPException(status_code=400, detail="Invalid email format")

    # Adaptive MFA / risk gate: evaluate before issuing tokens
    realm_for_policy = _detect_realm_from_email(email)
    tenant_for_policy = "unknown"
    policy_user_id = email
    user_roles: List[str] = []
    try:
        admin_client = KeycloakAdminClient()
        user_obj = await admin_client.get_user_by_username(realm_for_policy, email)
        if user_obj:
            policy_user_id = user_obj.get("id", email)
            attrs = user_obj.get("attributes") or {}
            tenant_attr = attrs.get("tenant_id") or attrs.get("tenant")
            if isinstance(tenant_attr, list) and tenant_attr:
                tenant_for_policy = tenant_attr[0]
            roles = await admin_client.get_user_realm_roles(realm_for_policy, policy_user_id)
            user_roles = [role.get("name") for role in roles if role.get("name")]
    except Exception as lookup_exc:
        logger.debug("Pre-login policy lookup failed for %s: %s", email, lookup_exc)

    # Skip adaptive MFA for demo realm/users to avoid blocking login in dev/demo
    skip_risk = realm_for_policy == "demo" or email.endswith("@demo.sentinelgrid.ai")
    if not skip_risk:
        try:
            mfa_policy = MFAPolicyService()
            risk_result = await mfa_policy.evaluate_mfa_requirement(
                user_id=policy_user_id,
                tenant_id=tenant_for_policy,
                device_id=None,
                ip_address=client_info.get("ip_address"),
                geo_location=None,
                time_of_day=datetime.utcnow(),
                target_app=request.app_id,
                requested_roles=user_roles,
            )
            if risk_result.get("mfa_required"):
                logger.info(
                    "Adaptive MFA required for %s (risk_score=%.1f, factors=%s)",
                    SecurityService.mask_sensitive_data(email),
                    risk_result.get("risk_score", 0),
                    risk_result.get("factors"),
                )
                raise HTTPException(
                    status_code=412,
                    detail={
                        "error": "mfa_required",
                        "message": "MFA required due to risk",
                        "risk_score": risk_result.get("risk_score"),
                        "factors": risk_result.get("factors"),
                    },
                )
        except HTTPException:
            raise
        except Exception as risk_exc:
            logger.debug(f"Risk evaluation skipped: {risk_exc}")

    try:
        token_data, realm_name, signup_completed, user_info = await _direct_login(
            email=email,
            password=request.password,
            client_info=client_info
        )

        AuditService.log_auth_event(
            realm_name=realm_name,
            action="user_login",
            actor_user_id=user_info["id"],
            actor_email=email,
            details={"remember_me": request.remember_me, "signup_completed": signup_completed},
            ip_address=client_info.get("ip_address"),
            user_agent=client_info.get("user_agent")
        )

        return LoginResponse(
            password_reset_required=False,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token", ""),
            expires_in=token_data.get("expires_in", 3600),
            token_type="Bearer",
            user=user_info,
            signup_completed=signup_completed
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True, extra=client_info)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during authentication"
        )


@public_router.post("/login/mfa")
async def login_with_mfa(
    request: LoginMFARequest,
    http_request: Request
):
    """
    Authenticate user with password + TOTP (for adaptive MFA challenge).
    """
    client_info = SecurityService.extract_client_info(http_request)
    email = SecurityService.sanitize_input(request.email)

    if not SecurityService.is_safe_email(email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    try:
        token_data, realm_name, signup_completed, user_info = await _direct_login(
            email=email,
            password=request.password,
            client_info=client_info,
            otp=request.otp,
        )

        AuditService.log_auth_event(
            realm_name=realm_name,
            action="user_login_mfa",
            actor_user_id=user_info["id"],
            actor_email=email,
            details={"remember_me": request.remember_me, "signup_completed": signup_completed, "mfa": "totp"},
            ip_address=client_info.get("ip_address"),
            user_agent=client_info.get("user_agent")
        )

        return LoginResponse(
            password_reset_required=False,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token", ""),
            expires_in=token_data.get("expires_in", 3600),
            token_type="Bearer",
            user=user_info,
            signup_completed=signup_completed
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MFA login error: {e}", exc_info=True, extra=client_info)
        raise HTTPException(status_code=500, detail="Internal server error during authentication")


@public_router.post("/reset-password-direct")
async def reset_password_direct():
    """Retire the legacy reset path without accessing accounts or credentials."""
    raise HTTPException(
        status_code=410,
        detail="Direct password reset has been removed. Use your identity provider's verified account recovery flow.",
    )


@public_router.post("/signup", response_model=SignupResponse)
async def signup(
    request: SignupRequest,
    http_request: Request
):
    """
    Create new customer account in Keycloak.
    Creates tenant, determines realm strategy, creates user.
    """
    # Extract client info for audit
    client_info = SecurityService.extract_client_info(http_request)
    
    # Sanitize inputs
    company_name = SecurityService.sanitize_input(request.company_name)
    email = SecurityService.sanitize_input(request.email)
    
    # Validate email safety
    if not SecurityService.is_safe_email(email):
        logger.warning(f"Unsafe email pattern detected: {email}", extra=client_info)
        raise HTTPException(
            status_code=400,
            detail="Invalid email format"
        )
    
    try:
        # Initialize new KeycloakAdminClient (direct REST API)
        async with KeycloakAdminClient() as kc_admin:
            # Check if email already exists
            existing_user = await kc_admin.get_user_by_username(settings.KEYCLOAK_REALM, email, exact=True)
            if existing_user:
                raise HTTPException(
                    status_code=409,
                    detail="An account with this email already exists"
                )
        
        # Auto-determine pricing tier from employee count if not provided
        pricing_tier = request.pricing_tier
        if not pricing_tier:
            pricing_tier = PricingService.determine_tier_from_employee_count(request.employee_count)
            logger.info(f"Auto-determined pricing tier '{pricing_tier}' from employee count {request.employee_count}")
        


        
        # Determine realm strategy (considering compliance requirements)
        realm_strategy = PricingService.get_realm_strategy(
            pricing_tier,
            user_count=0,
            org_count=0
        )

        # Compliance requirement always forces dedicated realm
        if request.compliance_required:
            realm_strategy = 'dedicated'
            logger.info(f"Compliance requirement forces dedicated realm for {company_name}")

        # Create customer in database
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        if not settings.DB_URL:
            raise HTTPException(
                status_code=500,
                detail="Database not configured"
            )

        engine = create_engine(settings.DB_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        db = SessionLocal()
        try:
            customer_id = uuid.uuid4()
            tenant_id = uuid.uuid4()
            realm_name = settings.KEYCLOAK_REALM

            if realm_strategy == 'dedicated':
                base_name = company_name.lower().replace(' ', '-')[:20]
                realm_name = f"{base_name}-{str(customer_id)[:8]}"
                logger.info(f"Generated dedicated realm name: {realm_name}")
                logger.warning("Dedicated realm creation not yet implemented with new client - using shared realm")
                realm_name = settings.KEYCLOAK_REALM

            # Generate unique slug from company name
            base_slug = company_name.lower().replace(' ', '-').replace('_', '-')
            import re
            base_slug = re.sub(r'[^a-z0-9-]', '', base_slug)
            if not base_slug:
                base_slug = 'tenant'

            existing_tenant = db.execute(
                text("SELECT id FROM tenants WHERE slug = :slug"),
                {"slug": base_slug}
            ).fetchone()
            slug = f"{base_slug}-{str(tenant_id)[:8]}" if existing_tenant else base_slug

            customer_columns = set(
                row[0]
                for row in db.execute(
                    text("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = 'customers'
                    """)
                ).fetchall()
            )

            customer_data = {
                "id": str(customer_id),
                "name": company_name,
                "slug": slug,
                "has_dedicated_realm": realm_strategy == 'dedicated',
                "pricing_tier": pricing_tier,
                "user_count": 1,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            if "realm_name" in customer_columns:
                customer_data["realm_name"] = realm_name if realm_strategy == 'dedicated' else None
            if "employee_count" in customer_columns:
                customer_data["employee_count"] = request.employee_count
            if "compliance_required" in customer_columns:
                customer_data["compliance_required"] = request.compliance_required
            if "signup_completed" in customer_columns:
                customer_data["signup_completed"] = False
            if "org_count" in customer_columns:
                customer_data["org_count"] = 0
            if "region" in customer_columns:
                customer_data["region"] = "us"
            if "status" in customer_columns:
                customer_data["status"] = "active"

            customer_columns_sql = ", ".join(customer_data.keys())
            customer_values_sql = ", ".join([f":{key}" for key in customer_data.keys()])

            db.execute(
                text(f"""
                    INSERT INTO customers ({customer_columns_sql})
                    VALUES ({customer_values_sql})
                """),
                customer_data,
            )

            db.execute(
                text('''
                    INSERT INTO tenants (id, name, slug, status, customer_id, created_at, updated_at)
                    VALUES (:id, :name, :slug, :status, :customer_id, :created_at, :updated_at)
                '''),
                {
                    "id": str(tenant_id),
                    "name": company_name,
                    "slug": slug,
                    "status": "active",
                    "customer_id": str(customer_id),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            )

            db.commit()

        except Exception as e:
            db.rollback()
            logger.error(f"Database error during signup: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Failed to create customer account"
            )
        finally:
            db.close()

        # Create user in Keycloak using new KeycloakAdminClient
        logger.info(f"Creating Keycloak user: {email} in realm: {realm_name}")

        try:
            user_id = await kc_admin.create_user(
                realm=realm_name,
                username=email,
                email=email,
                first_name=SecurityService.sanitize_input(request.first_name),
                last_name=SecurityService.sanitize_input(request.last_name),
                password=request.password,
                enabled=True,
                email_verified=False,
                attributes={
                    "tenant_id": [str(tenant_id)],
                    "customer_id": [str(customer_id)]
                },
                required_actions=[]
            )

            logger.info(f"✅ User created in Keycloak: {user_id}")

            try:
                await kc_admin.assign_realm_role(realm_name, user_id, "TENANT_ADMIN")
                logger.info(f"✅ Assigned TENANT_ADMIN role to user {user_id}")
            except Exception as e:
                logger.warning(f"Could not assign TENANT_ADMIN role: {e}")

        except Exception as e:
            logger.error(f"Failed to create user in Keycloak: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create user account: {str(e)}"
            )

        # Create user-tenant mapping
        engine = create_engine(settings.DB_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        try:
            db.execute(
                text('''
                    INSERT INTO user_tenants (user_id, tenant_id, customer_id, realm_name, created_at, updated_at)
                    VALUES (:user_id, :tenant_id, :customer_id, :realm_name, :created_at, :updated_at)
                '''),
                {
                    "user_id": user_id,
                    "tenant_id": str(tenant_id),
                    "customer_id": str(customer_id),
                    "realm_name": realm_name,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            )
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating user-tenant mapping: {e}", exc_info=True)
        finally:
            db.close()

        logger.info(f"New customer signup: {SecurityService.mask_sensitive_data(email)} ({company_name})", extra=client_info)

        AuditService.log_auth_event(
            realm_name=realm_name,
            action="user_signup",
            actor_email=email,
            customer_id=str(customer_id),
            details={
                "company_name": company_name,
                "pricing_tier": pricing_tier,
                "employee_count": request.employee_count,
                "compliance_required": request.compliance_required,
                "realm_strategy": realm_strategy
            },
            ip_address=client_info.get("ip_address"),
            user_agent=client_info.get("user_agent")
        )

        return SignupResponse(
            success=True,
            tenant_id=str(tenant_id),
            realm=realm_name,
            user_id=user_id,
            message="Account created successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True, extra=client_info)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during authentication"
        )
@public_router.post("/logout")
async def logout(
    refresh_token: str,
    http_request: Request
):
    """
    Logout user and invalidate Keycloak session.
    """
    # Extract client info for audit
    client_info = SecurityService.extract_client_info(http_request)
    
    try:
        validation = _require_validated_token(refresh_token, error_detail="Invalid refresh token")
        payload = validation["payload"]
        realm_name = _extract_realm_name(payload.get("iss"))
        user_id = validation.get("user_id")
        email = validation.get("email")
        
        # Logout from Keycloak (revoke refresh token)
        keycloak_url = settings.KEYCLOAK_URL
        logout_url = f"{keycloak_url}/realms/{realm_name}/protocol/openid-connect/logout"
        
        async with httpx.AsyncClient(timeout=10.0, verify=settings.KEYCLOAK_VERIFY_TLS) as client:
            await client.post(
                logout_url,
                data={
                    "client_id": "sentinelgrid-web",
                    "refresh_token": refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
        
        # Audit log
        AuditService.log_auth_event(
            realm_name=realm_name,
            action="user_logout",
            actor_user_id=user_id,
            actor_email=email,
            ip_address=client_info.get("ip_address"),
            user_agent=client_info.get("user_agent")
        )
        
        return {"success": True, "message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}", exc_info=True)
        # Don't fail logout even if audit fails
        return {"success": True, "message": "Logged out successfully"}


@public_router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    request: Request
):
    """
    Refresh access token using refresh token.
    """
    # Extract client info for audit
    client_info = SecurityService.extract_client_info(request)
    
    # Get refresh token from request body
    try:
        body = await request.json()
        refresh_token = body.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=400,
                detail="refresh_token is required"
            )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid request body"
        )
    
    try:
        refresh_validation = _require_validated_token(refresh_token, error_detail="Invalid refresh token")
        realm_name = _extract_realm_name(refresh_validation["payload"].get("iss"))
        
        # Refresh token with Keycloak
        keycloak_url = settings.KEYCLOAK_URL
        token_url = f"{keycloak_url}/realms/{realm_name}/protocol/openid-connect/token"
        
        async with httpx.AsyncClient(timeout=10.0, verify=settings.KEYCLOAK_VERIFY_TLS) as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": "sentinelgrid-web",
                    "refresh_token": refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=401,
                    detail="Token refresh failed"
                )
            
            token_data = response.json()
            
            access_validation = _require_validated_token(
                token_data["access_token"],
                error_detail="Invalid token returned by identity provider",
                status_code=500,
            )
            user_info = {
                "id": access_validation.get("user_id"),
                "email": access_validation.get("email"),
                "tenant_id": access_validation.get("tenant_id"),
                "roles": access_validation.get("roles", []),
            }
            
            # Audit log
            AuditService.log_auth_event(
                realm_name=realm_name,
                action="token_refresh",
                actor_user_id=user_info["id"],
                actor_email=user_info.get("email"),
                ip_address=client_info.get("ip_address"),
                user_agent=client_info.get("user_agent")
            )
            
            return LoginResponse(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", refresh_token),
                expires_in=token_data.get("expires_in", 3600),
                token_type="Bearer",
                user=user_info,
                password_reset_required=False
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error during token refresh"
        )


@public_router.get("/me")
async def get_current_user(
    request: Request
):
    """
    Get current user info from token.
    """
    authorization = request.headers.get("authorization")
    token = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "", 1)
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication token"
        )

    try:
        validation = _require_validated_token(token)
        payload = validation["payload"]
        return {
            "id": validation.get("user_id"),
            "email": validation.get("email"),
            "tenant_id": validation.get("tenant_id"),
            "roles": validation.get("roles", []),
            "plan_tier": validation.get("plan_tier"),
            "realm": _extract_realm_name(payload.get("iss")),
        }
        
    except Exception as e:
        logger.error(f"Error getting user info: {e}", exc_info=True)
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )


def get_customer_id_from_token(request: Request) -> str:
    """
    Extract customer_id from JWT token.
    TODO: Implement proper JWT validation and extraction
    """
    authorization = request.headers.get("authorization")
    default_tenant = getattr(settings, "SYSTEM_TENANT_ID", None) or os.getenv("DEFAULT_TENANT_ID") or "d1a542e3-7f68-4548-9519-c16ba285e23d"
    if not authorization or not authorization.startswith("Bearer "):
        fallback = request.headers.get("x-tenant-id") or request.headers.get("X-Tenant-ID")
        return fallback or default_tenant
    
    token = authorization.replace("Bearer ", "")
    
    try:
        validation = _require_validated_token(token)
        payload = validation["payload"]
        customer_id = validation.get("tenant_id") or payload.get("customer_id")
        if customer_id:
            return customer_id
        return default_tenant
    except HTTPException as exc:
        logger.error(f"Error extracting customer_id from token: {exc.detail}")
        raise
