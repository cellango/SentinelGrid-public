"""
Signup API - Customer self-service registration with realm-aware provisioning.
Handles signup flow with automatic region detection, pricing tier determination,
and realm assignment.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy.orm import Session
import re
from typing import Dict, Any

from app.core.database import get_db
from app.core.keycloak import KeycloakAdminClient
from app.services.enhanced_provisioning_service import EnhancedProvisioningService
from app.services.onboarding_scans import trigger_initial_scans

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/signup", tags=["signup"])


class SignupRequest(BaseModel):
    """Signup request model."""
    
    # Company information
    company_name: str = Field(..., min_length=2, max_length=255, description="Company name")
    tenant_slug: Optional[str] = Field(
        None,
        min_length=3,
        max_length=40,
        description="Tenant short/slug (lowercase letters/numbers/hyphen, immutable)",
    )
    employee_count: Optional[int] = Field(None, ge=1, le=1000000, description="Number of employees")
    industry: Optional[str] = Field(None, max_length=100, description="Industry")
    
    # Admin user information
    admin_email: EmailStr = Field(..., description="Admin email address")
    admin_password: str = Field(..., min_length=8, max_length=100, description="Admin password")
    admin_first_name: str = Field(..., min_length=1, max_length=100, description="Admin first name")
    admin_last_name: str = Field(..., min_length=1, max_length=100, description="Admin last name")
    
    # Optional fields
    region: Optional[str] = Field(None, pattern="^(us|eu|ap|sa|me|af)$", description="Preferred region")
    compliance_required: bool = Field(default=False, description="Compliance requirements mandate dedicated realm")
    services_selected: Optional[Dict[str, Any]] = Field(default=None, description="Selected services/add-ons")
    tenant_slug: Optional[str] = Field(
        None,
        min_length=3,
        max_length=40,
        description="Tenant short/slug (lowercase letters/numbers/hyphen, immutable)",
    )
    
    # Terms acceptance
    terms_accepted: bool = Field(..., description="Terms of service accepted")
    privacy_accepted: bool = Field(..., description="Privacy policy accepted")
    
    @field_validator('admin_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Validate password strength.
        Must contain: uppercase, lowercase, digit, and be at least 8 characters.
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        return v
    
    @field_validator('company_name')
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        """Validate and sanitize company name."""
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Company name must be at least 2 characters")
        return v

    @field_validator('tenant_slug')
    @classmethod
    def validate_tenant_slug(cls, v: Optional[str]) -> Optional[str]:
        """Enforce slug pattern and reserved words."""
        if v is None:
            return v
        slug = v.strip().lower()
        if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{1,38}[a-z0-9])?', slug):
            raise ValueError("tenant_slug must be 3-40 chars, lowercase letters/numbers/hyphen, no leading/trailing hyphen")
        if '--' in slug:
            raise ValueError("tenant_slug cannot contain consecutive hyphens")
        reserved = {'admin', 'master', 'keycloak', 'sentinelgrid', 'demo'}
        if slug in reserved:
            raise ValueError("tenant_slug is reserved")
        return slug
    
    @field_validator('terms_accepted', 'privacy_accepted')
    @classmethod
    def validate_acceptance(cls, v: bool) -> bool:
        """Ensure terms and privacy are accepted."""
        if not v:
            raise ValueError("You must accept the terms of service and privacy policy")
        return v


class SignupResponse(BaseModel):
    """Signup response model."""
    success: bool
    message: str
    tenant_id: Optional[str] = None
    customer_id: Optional[str] = None
    realm_name: Optional[str] = None
    pricing_tier: Optional[str] = None
    region: Optional[str] = None
    next_steps: Optional[list] = None


class RegionDetectionResponse(BaseModel):
    """Region detection response."""
    region: str
    country: Optional[str] = None
    suggested: bool


def get_keycloak_client() -> KeycloakAdminClient:
    """Dependency to get Keycloak admin client."""
    return KeycloakAdminClient()


def get_provisioning_service(
    db: Session = Depends(get_db),
    keycloak_client: KeycloakAdminClient = Depends(get_keycloak_client)
) -> EnhancedProvisioningService:
    """Dependency to get enhanced provisioning service."""
    return EnhancedProvisioningService(db, keycloak_client.admin)


@router.post("/", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    request: SignupRequest,
    http_request: Request,
    service: EnhancedProvisioningService = Depends(get_provisioning_service)
):
    """
    Customer self-service signup endpoint.
    
    This endpoint:
    1. Validates signup request
    2. Detects region (if not provided)
    3. Determines pricing tier from employee count
    4. Provisions customer, tenant, and realm
    5. Creates admin user in Keycloak
    6. Returns signup confirmation
    
    **Public endpoint - no authentication required**
    """
    try:
        logger.info(f"📝 Signup request received for company: {request.company_name}")
        
        # Detect region if not provided
        region = request.region
        if not region:
            region = _detect_region_from_request(http_request)
            logger.info(f"🌍 Detected region: {region}")
        
        # Provision tenant
        result = service.provision_tenant(
            company_name=request.company_name,
            admin_email=request.admin_email,
            admin_password=request.admin_password,
            admin_first_name=request.admin_first_name,
            admin_last_name=request.admin_last_name,
            employee_count=request.employee_count,
            region=region,
            compliance_required=request.compliance_required,
            industry=request.industry,
            tenant_slug=request.tenant_slug,
            services_selected=request.services_selected,
        )
        # Best-effort: trigger initial scans after health check
        trigger_initial_scans(result["tenant_id"])
        
        # Determine next steps based on pricing tier
        next_steps = _get_next_steps(result["pricing_tier"], result["realm_name"])
        
        logger.info(f"✅ Signup completed for {request.company_name}")
        
        return SignupResponse(
            success=True,
            message=f"Welcome to SentinelGrid! Your account has been created successfully.",
            tenant_id=result["tenant_id"],
            customer_id=result["customer_id"],
            realm_name=result["realm_name"],
            pricing_tier=result["pricing_tier"],
            region=result["region"],
            next_steps=next_steps
        )
        
    except ValueError as e:
        # Validation errors
        logger.warning(f"Signup validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"❌ Signup failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signup failed. Please try again or contact support."
        )


@router.get("/detect-region", response_model=RegionDetectionResponse)
async def detect_region(request: Request):
    """
    Detect user's region from IP address.
    Used by frontend to suggest region during signup.
    
    **Public endpoint - no authentication required**
    """
    try:
        region = _detect_region_from_request(request)
        
        return RegionDetectionResponse(
            region=region,
            country=None,  # Could be enhanced with GeoIP lookup
            suggested=True
        )
    except Exception as e:
        logger.error(f"Region detection failed: {e}")
        # Default to US if detection fails
        return RegionDetectionResponse(
            region="us",
            country=None,
            suggested=False
        )


@router.get("/check-availability/{slug}")
async def check_slug_availability(
    slug: str,
    db: Session = Depends(get_db)
):
    """
    Check if company slug is available.
    Used by frontend for real-time validation.
    
    **Public endpoint - no authentication required**
    """
    try:
        # Validate slug format
        if not re.match(r'^[a-z0-9-]+$', slug):
            return {
                "available": False,
                "message": "Slug can only contain lowercase letters, numbers, and hyphens"
            }
        
        if len(slug) < 3:
            return {
                "available": False,
                "message": "Slug must be at least 3 characters long"
            }
        
        # Check database
        from sqlalchemy import text
        result = db.execute(
            text("SELECT 1 FROM customers WHERE slug = :slug LIMIT 1"),
            {"slug": slug}
        ).first()
        
        available = result is None
        
        return {
            "available": available,
            "message": "Slug is available" if available else "Slug is already taken"
        }
        
    except Exception as e:
        logger.error(f"Slug availability check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not check slug availability"
        )


@router.get("/pricing-tiers")
async def get_pricing_tiers():
    """
    Get available pricing tiers with features and limits.
    Used by frontend to display pricing information.
    
    **Public endpoint - no authentication required**
    """
    # Import here to avoid circular dependency
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../agents/iam_agent/app"))
    from services.pricing_service import PricingService
    
    tiers = ["free", "starter", "professional", "enterprise"]
    
    return {
        "tiers": [
            PricingService.get_pricing_info(tier)
            for tier in tiers
        ]
    }


def _detect_region_from_request(request: Request) -> str:
    """
    Detect region from HTTP request.
    
    Priority:
    1. CloudFront-Viewer-Country header (if behind CloudFront)
    2. CF-IPCountry header (if behind Cloudflare)
    3. X-Forwarded-For IP geolocation
    4. Default to 'us'
    
    Args:
        request: FastAPI Request object
    
    Returns:
        Region code (us, eu, ap, sa, me, af)
    """
    # Check CloudFront header
    cf_country = request.headers.get("CloudFront-Viewer-Country")
    if cf_country:
        return _country_to_region(cf_country)
    
    # Check Cloudflare header
    cf_country = request.headers.get("CF-IPCountry")
    if cf_country:
        return _country_to_region(cf_country)
    
    # TODO: Implement IP geolocation using MaxMind GeoIP2 or similar
    # For now, default to US
    return "us"


def _country_to_region(country_code: str) -> str:
    """
    Map country code to region.
    
    Args:
        country_code: ISO 3166-1 alpha-2 country code
    
    Returns:
        Region code
    """
    # European countries
    eu_countries = {
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
        "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
        "PL", "PT", "RO", "SK", "SI", "ES", "SE", "GB", "CH", "NO",
        "IS", "LI"
    }
    
    # Asia-Pacific countries
    ap_countries = {
        "AU", "NZ", "JP", "KR", "CN", "HK", "TW", "SG", "MY", "TH",
        "ID", "PH", "VN", "IN", "PK", "BD"
    }
    
    # South American countries
    sa_countries = {
        "BR", "AR", "CL", "CO", "PE", "VE", "EC", "BO", "PY", "UY",
        "GY", "SR", "GF"
    }
    
    # Middle Eastern countries
    me_countries = {
        "AE", "SA", "IL", "TR", "EG", "IQ", "IR", "JO", "KW", "LB",
        "OM", "QA", "SY", "YE", "BH"
    }
    
    # African countries
    af_countries = {
        "ZA", "NG", "KE", "GH", "TZ", "UG", "ET", "MA", "DZ", "TN",
        "LY", "SD", "AO", "MZ", "ZW", "ZM", "MW", "BW", "NA", "SN"
    }
    
    country_code = country_code.upper()
    
    if country_code in eu_countries:
        return "eu"
    elif country_code in ap_countries:
        return "ap"
    elif country_code in sa_countries:
        return "sa"
    elif country_code in me_countries:
        return "me"
    elif country_code in af_countries:
        return "af"
    else:
        return "us"  # Default to US for North America and others


def _get_next_steps(pricing_tier: str, realm_name: str) -> list:
    """
    Get next steps for customer based on pricing tier.
    
    Args:
        pricing_tier: Pricing tier
        realm_name: Assigned realm name
    
    Returns:
        List of next steps
    """
    base_steps = [
        {
            "step": 1,
            "title": "Check your email",
            "description": "We've sent a verification email to confirm your account."
        },
        {
            "step": 2,
            "title": "Log in to your dashboard",
            "description": f"Access your dashboard at https://app.sentinelgrid.com"
        },
        {
            "step": 3,
            "title": "Connect your identity provider",
            "description": "Integrate with Google Workspace, Microsoft 365, or Okta for user sync."
        },
        {
            "step": 4,
            "title": "Connect your cloud provider",
            "description": "Link AWS, Azure, or GCP for security monitoring."
        },
        {
            "step": 5,
            "title": "Deploy SentinelGrid agents",
            "description": "Install endpoint protection agents on your devices."
        }
    ]
    
    # Add tier-specific steps
    if pricing_tier == "enterprise":
        base_steps.insert(2, {
            "step": 2.5,
            "title": "Schedule onboarding call",
            "description": "Our team will reach out to schedule a personalized onboarding session."
        })
    
    return base_steps
