"""
Leads API endpoints for handling incomplete signups and demo requests.
Leads are created before payment and can later be converted to accounts.
"""

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, validator
from typing import Any, Optional
import logging
from datetime import datetime, timedelta
import secrets
import hmac
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import bcrypt
import json
import uuid

from app.core.config import settings
from app.services.payment_service import PaymentService
from app.services.security import SecurityService
from sg_core.product_catalog import (
    apply_plan_defaults,
    derive_plan_tier,
    normalize_plan_tier,
    plan_includes_compliance,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])

DEMO_COMPANY_SIZE_TO_USER_COUNT = {
    "1-25 employees": 25,
    "26-100 employees": 100,
    "101-250 employees": 250,
    "251-1000 employees": 1000,
    "1000+ employees": 1001,
}

DEMO_ALLOWED_MOTIONS = {"standard", "partner"}
DEMO_ALLOWED_IDENTITY_PROFILES = {
    "microsoft_entra",
    "google_workspace",
    "okta",
    "mixed",
}
DEMO_ALLOWED_ROLLOUT_SCOPES = {"single_environment", "multi_environment"}
DEMO_ALLOWED_RETENTION_PROFILES = {"standard", "extended_or_archive"}
DEMO_ALLOWED_AI_SHIELD_FITS = {"none", "add_on", "primary"}


def _coerce_lead_metadata(raw_metadata: Any) -> dict:
    if not raw_metadata:
        return {}

    if isinstance(raw_metadata, dict):
        return dict(raw_metadata)

    if isinstance(raw_metadata, str):
        try:
            parsed = json.loads(raw_metadata)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed

    return {}


def _serialize_lead_metadata(metadata: Optional[dict]) -> Optional[str]:
    if not metadata:
        return None
    return json.dumps(metadata)


def _extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    return token.strip()


def _validate_provisioning_token(lead_metadata: Any, presented_token: str) -> None:
    stored_token = _coerce_lead_metadata(lead_metadata).get("provisioning_token")
    if not isinstance(stored_token, str) or not stored_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid provisioning token")
    if not hmac.compare_digest(stored_token, presented_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid provisioning token")


def _build_lead_metadata(
    existing_metadata: Any = None,
    *,
    services_selected: Optional[dict] = None,
    plan_tier: Optional[str] = None,
    lead_source: Optional[str] = None,
    demo_request: Optional[dict] = None,
    tenant_slug: Optional[str] = None,
) -> Optional[dict]:
    metadata = _coerce_lead_metadata(existing_metadata)

    if services_selected is not None:
        metadata["services_selected"] = services_selected

    if plan_tier:
        metadata["plan_tier"] = plan_tier

    if lead_source:
        metadata["lead_source"] = lead_source

    if demo_request is not None:
        metadata["demo_request"] = demo_request

    if tenant_slug:
        metadata["tenant_slug"] = tenant_slug

    return metadata or None


def _estimate_demo_user_count(company_size: str) -> int:
    return DEMO_COMPANY_SIZE_TO_USER_COUNT.get(company_size, 25)


def _build_demo_request_payload(
    existing_metadata: Any,
    *,
    company_size: str,
    notes: Optional[str],
    source: str,
    plan_tier: Optional[str],
    qualification: dict,
    requested_at: datetime,
) -> dict:
    metadata = _coerce_lead_metadata(existing_metadata)
    existing_demo_request = metadata.get("demo_request")
    if not isinstance(existing_demo_request, dict):
        existing_demo_request = {}

    request_count = existing_demo_request.get("request_count", 0)
    if not isinstance(request_count, int):
        request_count = 0

    metadata["demo_request"] = {
        "first_requested_at": existing_demo_request.get("first_requested_at") or requested_at.isoformat(),
        "last_requested_at": requested_at.isoformat(),
        "request_count": request_count + 1,
        "company_size": company_size,
        "notes": notes,
        "source": source,
        "status": "submitted",
        "qualification": qualification,
    }

    if plan_tier:
        metadata["plan_tier"] = plan_tier

    metadata["lead_source"] = "demo_request"
    return metadata


def _build_demo_qualification_context(
    *,
    motion: str,
    identity_profile: str,
    rollout_scope: str,
    retention_profile: str,
    ai_shield_fit: str,
) -> dict:
    guided_review_reasons: list[str] = []

    if motion == "partner":
        guided_review_reasons.append("partner_motion")
    if identity_profile == "mixed":
        guided_review_reasons.append("mixed_identity")
    if rollout_scope == "multi_environment":
        guided_review_reasons.append("multi_environment")
    if retention_profile == "extended_or_archive":
        guided_review_reasons.append("extended_retention_or_trust_review")
    if ai_shield_fit == "primary":
        guided_review_reasons.append("ai_shield_primary")

    return {
        "motion": motion,
        "identity_profile": identity_profile,
        "rollout_scope": rollout_scope,
        "retention_profile": retention_profile,
        "ai_shield_fit": ai_shield_fit,
        "guided_review_reasons": guided_review_reasons,
        "recommended_path": "guided_review"
        if guided_review_reasons
        else "standard_launch_path",
    }


class CreateLeadRequest(BaseModel):
    """Request to create a lead (incomplete signup)."""
    email: str
    company_name: str
    first_name: str
    last_name: str
    password: str
    user_count: int
    compliance_required: bool = False
    plan_tier: Optional[str] = None
    tenant_slug: Optional[str] = None
    services_selected: Optional[dict] = None
    
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
    
    @validator('user_count')
    def validate_user_count(cls, v):
        if v < 1:
            raise ValueError('User count must be at least 1')
        if v > 100000:
            raise ValueError('User count seems too large. Please contact sales for enterprise pricing.')
        return v

    @validator('plan_tier')
    def validate_plan_tier(cls, v):
        if v is None:
            return v
        normalized = normalize_plan_tier(v)
        if normalized is None:
            raise ValueError('Invalid plan tier')
        return normalized

    @validator('tenant_slug')
    def validate_tenant_slug(cls, v):
        if v is None:
            return v
        slug = v.strip().lower()
        if not slug:
            return None
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{1,38}[a-z0-9])?", slug):
            raise ValueError('Tenant slug must be 3-40 chars, lowercase letters, numbers, or hyphens')
        return slug


class UpdateLeadRequest(BaseModel):
    """Request to update an existing lead after plan selection changes."""

    compliance_required: Optional[bool] = None
    plan_tier: Optional[str] = None
    tenant_slug: Optional[str] = None
    services_selected: Optional[dict] = None

    @validator('plan_tier')
    def validate_plan_tier(cls, v):
        if v is None:
            return v
        normalized = normalize_plan_tier(v)
        if normalized is None:
            raise ValueError('Invalid plan tier')
        return normalized

    @validator('tenant_slug')
    def validate_tenant_slug(cls, v):
        if v is None:
            return v
        slug = v.strip().lower()
        if not slug:
            return None
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{1,38}[a-z0-9])?", slug):
            raise ValueError('Tenant slug must be 3-40 chars, lowercase letters, numbers, or hyphens')
        return slug


class CreateDemoRequestRequest(BaseModel):
    """Request to capture a guided demo request."""
    email: str
    company_name: str
    first_name: str
    last_name: str
    company_size: str
    notes: Optional[str] = None
    plan_tier: Optional[str] = None
    source: str = "demo_page_form"
    motion: str = "standard"
    identity_profile: str = "microsoft_entra"
    rollout_scope: str = "single_environment"
    retention_profile: str = "standard"
    ai_shield_fit: str = "none"

    @validator('email')
    def validate_email(cls, v):
        if '@' not in v or '.' not in v.split('@')[1]:
            raise ValueError('Invalid email format')
        return v.lower().strip()

    @validator('company_size')
    def validate_company_size(cls, v):
        if v not in DEMO_COMPANY_SIZE_TO_USER_COUNT:
            raise ValueError('Invalid company size selection')
        return v

    @validator('notes')
    def validate_notes(cls, v):
        if v is None:
            return v
        note_text = v.strip()
        if len(note_text) > 2000:
            raise ValueError('Notes must be 2000 characters or fewer')
        return note_text

    @validator('plan_tier')
    def validate_plan_tier(cls, v):
        if v is None:
            return v
        normalized = normalize_plan_tier(v)
        if normalized is None:
            raise ValueError('Invalid plan tier')
        return normalized

    @validator('source')
    def validate_source(cls, v):
        value = v.strip()
        if not value:
            raise ValueError('Source is required')
        if len(value) > 100:
            raise ValueError('Source is too long')
        return value

    @validator('motion')
    def validate_motion(cls, v):
        value = v.strip()
        if value not in DEMO_ALLOWED_MOTIONS:
            raise ValueError('Invalid demo motion')
        return value

    @validator('identity_profile')
    def validate_identity_profile(cls, v):
        value = v.strip()
        if value not in DEMO_ALLOWED_IDENTITY_PROFILES:
            raise ValueError('Invalid identity profile')
        return value

    @validator('rollout_scope')
    def validate_rollout_scope(cls, v):
        value = v.strip()
        if value not in DEMO_ALLOWED_ROLLOUT_SCOPES:
            raise ValueError('Invalid rollout scope')
        return value

    @validator('retention_profile')
    def validate_retention_profile(cls, v):
        value = v.strip()
        if value not in DEMO_ALLOWED_RETENTION_PROFILES:
            raise ValueError('Invalid retention profile')
        return value

    @validator('ai_shield_fit')
    def validate_ai_shield_fit(cls, v):
        value = v.strip()
        if value not in DEMO_ALLOWED_AI_SHIELD_FITS:
            raise ValueError('Invalid AI Shield fit')
        return value


class LeadResponse(BaseModel):
    """Response after creating a lead."""
    success: bool
    lead_id: str
    session_token: Optional[str] = None
    pricing: dict
    message: str


class DemoRequestResponse(BaseModel):
    """Response after creating or updating a demo request."""
    success: bool
    lead_id: str
    message: str


@router.post("/create", response_model=LeadResponse)
async def create_lead(
    request: CreateLeadRequest,
    http_request: Request
):
    """
    Create a lead (incomplete signup) before payment.
    Stores information but does not create Keycloak account.
    """
    # Extract client info for audit
    client_info = SecurityService.extract_client_info(http_request)
    
    # Sanitize inputs
    email = SecurityService.sanitize_input(request.email)
    company_name = SecurityService.sanitize_input(request.company_name)
    
    # Validate email safety
    if not SecurityService.is_safe_email(email):
        logger.warning(f"Unsafe email pattern detected: {email}", extra=client_info)
        raise HTTPException(
            status_code=400,
            detail="Invalid email format"
        )
    
    try:
        # Check if email already exists (as lead or customer)
        if not settings.DB_URL:
            raise HTTPException(
                status_code=500,
                detail="Database not configured"
            )
        
        engine = create_engine(settings.DB_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # Check for existing lead
            existing_lead = db.execute(
                text("SELECT id, status, metadata FROM leads WHERE email = :email"),
                {"email": email}
            ).fetchone()
            
            if existing_lead:
                # If already converted, don't allow new lead
                if existing_lead[1] == 'converted':
                    raise HTTPException(
                        status_code=409,
                        detail="An account with this email already exists"
                    )
                # If pending, update it
                lead_id = existing_lead[0]
                logger.info(f"Updating existing lead {lead_id} for {SecurityService.mask_sensitive_data(email)}")
            else:
                # Check for existing customer (via Keycloak lookup would be better, but this works)
                existing_customer = db.execute(
                    text("SELECT id FROM customers WHERE name = :name OR id IN (SELECT customer_id FROM tenants WHERE name = :name)"),
                    {"name": company_name}
                ).fetchone()
                
                if existing_customer:
                    raise HTTPException(
                        status_code=409,
                        detail="An account with this email or company already exists"
                    )
                
                lead_id = str(uuid.uuid4())
            
            normalized_plan_tier = derive_plan_tier(
                plan_tier=request.plan_tier,
                compliance_required=request.compliance_required,
                services_selected=request.services_selected,
            )
            normalized_services = apply_plan_defaults(
                normalized_plan_tier,
                request.services_selected,
            )
            compliance_required = plan_includes_compliance(normalized_plan_tier)

            pricing = PaymentService.calculate_price(
                user_count=request.user_count,
                compliance_required=compliance_required,
                plan_tier=normalized_plan_tier,
                billing_period="monthly",  # Default to monthly for lead creation
                services_selected=normalized_services,
            )
            
            # Hash password securely
            password_hash = bcrypt.hashpw(
                request.password.encode('utf-8'),
                bcrypt.gensalt()
            ).decode('utf-8')
            
            # Determine user band and package
            user_band = PaymentService.get_user_band(request.user_count)
            package_name = PaymentService.get_package_name(
                compliance_required,
                plan_tier=normalized_plan_tier,
                services_selected=normalized_services,
            )
            
            # Set expiration (30 days from now)
            expires_at = datetime.utcnow() + timedelta(days=30)
            
            # Prepare metadata as JSONB
            provisioning_token = secrets.token_urlsafe(32)
            metadata = _build_lead_metadata(
                existing_lead[2] if existing_lead else None,
                services_selected=normalized_services,
                plan_tier=normalized_plan_tier,
                lead_source="signup",
                tenant_slug=request.tenant_slug,
            ) or {}
            metadata["provisioning_token"] = provisioning_token
            metadata = _serialize_lead_metadata(metadata)

            # Create or update lead
            if existing_lead and existing_lead[1] != 'converted':
                # Update existing lead
                db.execute(
                    text("""
                        UPDATE leads 
                        SET company_name = :company_name,
                            first_name = :first_name,
                            last_name = :last_name,
                            password_hash = :password_hash,
                            user_count = :user_count,
                            user_band = :user_band,
                            compliance_required = :compliance_required,
                            package_name = :package_name,
                            estimated_price_cents = :estimated_price_cents,
                            metadata = CAST(:metadata AS jsonb),
                            status = 'pending',
                            updated_at = :updated_at,
                            expires_at = :expires_at
                        WHERE id = :id
                    """),
                    {
                        "id": lead_id,
                        "company_name": company_name,
                        "first_name": SecurityService.sanitize_input(request.first_name),
                        "last_name": SecurityService.sanitize_input(request.last_name),
                        "password_hash": password_hash,
                        "user_count": request.user_count,
                        "user_band": user_band,
                        "compliance_required": compliance_required,
                        "package_name": package_name,
                        "estimated_price_cents": pricing['total'] if pricing['total'] is not None else None,
                        "metadata": metadata,
                        "updated_at": datetime.utcnow(),
                        "expires_at": expires_at
                    }
                )
            else:
                # Create new lead
                db.execute(
                    text("""
                        INSERT INTO leads (
                            id, email, company_name, first_name, last_name, password_hash,
                            user_count, user_band, compliance_required, package_name,
                            estimated_price_cents, status, expires_at, created_at, updated_at, metadata
                        )
                        VALUES (
                            :id, :email, :company_name, :first_name, :last_name, :password_hash,
                            :user_count, :user_band, :compliance_required, :package_name,
                            :estimated_price_cents, 'pending', :expires_at, :created_at, :updated_at, CAST(:metadata AS jsonb)
                        )
                    """),
                    {
                        "id": lead_id,
                        "email": email,
                        "company_name": company_name,
                        "first_name": SecurityService.sanitize_input(request.first_name),
                        "last_name": SecurityService.sanitize_input(request.last_name),
                        "password_hash": password_hash,
                        "user_count": request.user_count,
                        "user_band": user_band,
                        "compliance_required": compliance_required,
                        "package_name": package_name,
                        "estimated_price_cents": pricing['total'] if pricing['total'] is not None else None,
                        "expires_at": expires_at,
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                        "metadata": metadata
                    }
                )
            
            db.commit()
            
            logger.info(f"Lead created/updated: {lead_id} for {SecurityService.mask_sensitive_data(email)}")
            
            return LeadResponse(
                success=True,
                lead_id=lead_id,
                session_token=provisioning_token,
                pricing=pricing,
                message="Lead created successfully. Proceed to payment to create your account."
            )
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating lead: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Failed to create lead"
            )
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_lead: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.post("/demo-request", response_model=DemoRequestResponse)
async def create_demo_request(
    request: CreateDemoRequestRequest,
    http_request: Request
):
    """
    Create or update a lead record for a guided demo request.
    This keeps demo intake in the same lead model used by later signup.
    """
    client_info = SecurityService.extract_client_info(http_request)

    email = SecurityService.sanitize_input(request.email)
    company_name = SecurityService.sanitize_input(request.company_name)
    first_name = SecurityService.sanitize_input(request.first_name)
    last_name = SecurityService.sanitize_input(request.last_name)
    notes = SecurityService.sanitize_input(request.notes) if request.notes else None

    if not SecurityService.is_safe_email(email):
        logger.warning(f"Unsafe email pattern detected: {email}", extra=client_info)
        raise HTTPException(
            status_code=400,
            detail="Invalid email format"
        )

    try:
        if not settings.DB_URL:
            raise HTTPException(
                status_code=500,
                detail="Database not configured"
            )

        engine = create_engine(settings.DB_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        try:
            existing_lead = db.execute(
                text("SELECT id, status, metadata FROM leads WHERE email = :email"),
                {"email": email}
            ).fetchone()

            if existing_lead and existing_lead[1] == "converted":
                raise HTTPException(
                    status_code=409,
                    detail="An account with this email already exists. Sign in or contact support."
                )

            requested_at = datetime.utcnow()
            expires_at = requested_at + timedelta(days=30)
            user_count = _estimate_demo_user_count(request.company_size)
            normalized_plan_tier = derive_plan_tier(plan_tier=request.plan_tier)
            compliance_required = plan_includes_compliance(normalized_plan_tier)
            pricing = PaymentService.calculate_price(
                user_count=user_count,
                compliance_required=compliance_required,
                plan_tier=normalized_plan_tier,
                billing_period="monthly",
                services_selected={},
            )
            user_band = PaymentService.get_user_band(user_count)
            package_name = PaymentService.get_package_name(
                compliance_required,
                plan_tier=normalized_plan_tier,
                services_selected={},
            )
            qualification = _build_demo_qualification_context(
                motion=request.motion,
                identity_profile=request.identity_profile,
                rollout_scope=request.rollout_scope,
                retention_profile=request.retention_profile,
                ai_shield_fit=request.ai_shield_fit,
            )
            metadata = _build_demo_request_payload(
                existing_lead[2] if existing_lead else None,
                company_size=request.company_size,
                notes=notes,
                source=request.source,
                plan_tier=normalized_plan_tier,
                qualification=qualification,
                requested_at=requested_at,
            )
            metadata_json = _serialize_lead_metadata(metadata)

            if existing_lead:
                lead_id = existing_lead[0]
                db.execute(
                    text("""
                        UPDATE leads
                        SET company_name = :company_name,
                            first_name = :first_name,
                            last_name = :last_name,
                            user_count = :user_count,
                            user_band = :user_band,
                            compliance_required = :compliance_required,
                            package_name = :package_name,
                            estimated_price_cents = :estimated_price_cents,
                            metadata = CAST(:metadata AS jsonb),
                            updated_at = :updated_at,
                            expires_at = :expires_at
                        WHERE id = :id
                    """),
                    {
                        "id": lead_id,
                        "company_name": company_name,
                        "first_name": first_name,
                        "last_name": last_name,
                        "user_count": user_count,
                        "user_band": user_band,
                        "compliance_required": compliance_required,
                        "package_name": package_name,
                        "estimated_price_cents": pricing["total"] if pricing["total"] is not None else None,
                        "metadata": metadata_json,
                        "updated_at": requested_at,
                        "expires_at": expires_at,
                    }
                )
            else:
                lead_id = str(uuid.uuid4())
                db.execute(
                    text("""
                        INSERT INTO leads (
                            id, email, company_name, first_name, last_name, password_hash,
                            user_count, user_band, compliance_required, package_name,
                            estimated_price_cents, status, expires_at, created_at, updated_at, metadata
                        )
                        VALUES (
                            :id, :email, :company_name, :first_name, :last_name, NULL,
                            :user_count, :user_band, :compliance_required, :package_name,
                            :estimated_price_cents, 'pending', :expires_at, :created_at, :updated_at, CAST(:metadata AS jsonb)
                        )
                    """),
                    {
                        "id": lead_id,
                        "email": email,
                        "company_name": company_name,
                        "first_name": first_name,
                        "last_name": last_name,
                        "user_count": user_count,
                        "user_band": user_band,
                        "compliance_required": compliance_required,
                        "package_name": package_name,
                        "estimated_price_cents": pricing["total"] if pricing["total"] is not None else None,
                        "expires_at": expires_at,
                        "created_at": requested_at,
                        "updated_at": requested_at,
                        "metadata": metadata_json,
                    }
                )

            db.commit()

            logger.info(
                "Demo request created/updated: %s for %s",
                lead_id,
                SecurityService.mask_sensitive_data(email),
            )

            return DemoRequestResponse(
                success=True,
                lead_id=lead_id,
                message="Demo request received. We will reach out shortly to schedule your walkthrough.",
            )

        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating demo request: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Failed to create demo request"
            )
        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_demo_request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: str,
    request: UpdateLeadRequest,
    authorization: Optional[str] = Header(default=None),
):
    """Update an existing lead's canonical plan and signup selections."""
    if not settings.DB_URL:
        raise HTTPException(status_code=500, detail="Database not configured")

    engine = create_engine(settings.DB_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        provisioning_token = _extract_bearer_token(authorization)
        lead = db.execute(
            text(
                """
                SELECT id, user_count, compliance_required, package_name, metadata, expires_at, status
                FROM leads
                WHERE id = :lead_id
                """
            ),
            {"lead_id": lead_id},
        ).mappings().fetchone()

        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        _validate_provisioning_token(lead.get("metadata"), provisioning_token)

        if lead["status"] == "converted":
            raise HTTPException(status_code=400, detail="Lead already converted to account")

        if lead["expires_at"] and lead["expires_at"] < datetime.utcnow():
            raise HTTPException(status_code=410, detail="Lead has expired")

        existing_metadata = _coerce_lead_metadata(lead.get("metadata"))
        merged_services = (
            request.services_selected
            if request.services_selected is not None
            else existing_metadata.get("services_selected")
        )
        normalized_plan_tier = derive_plan_tier(
            plan_tier=request.plan_tier or existing_metadata.get("plan_tier"),
            package_name=lead.get("package_name"),
            compliance_required=request.compliance_required
            if request.compliance_required is not None
            else lead.get("compliance_required", False),
            services_selected=merged_services,
        )
        normalized_services = apply_plan_defaults(normalized_plan_tier, merged_services)
        compliance_required = plan_includes_compliance(normalized_plan_tier)
        pricing = PaymentService.calculate_price(
            user_count=lead["user_count"],
            compliance_required=compliance_required,
            plan_tier=normalized_plan_tier,
            billing_period="monthly",
            services_selected=normalized_services,
        )

        metadata = _build_lead_metadata(
            existing_metadata,
            services_selected=normalized_services,
            plan_tier=normalized_plan_tier,
            tenant_slug=request.tenant_slug or existing_metadata.get("tenant_slug"),
        ) or {}
        metadata["provisioning_token"] = existing_metadata.get("provisioning_token") or provisioning_token
        metadata_json = _serialize_lead_metadata(metadata)

        db.execute(
            text(
                """
                UPDATE leads
                SET compliance_required = :compliance_required,
                    package_name = :package_name,
                    estimated_price_cents = :estimated_price_cents,
                    metadata = CAST(:metadata AS jsonb),
                    updated_at = :updated_at
                WHERE id = :lead_id
                """
            ),
            {
                "lead_id": lead_id,
                "compliance_required": compliance_required,
                "package_name": normalized_plan_tier,
                "estimated_price_cents": pricing["total"] if pricing["total"] is not None else None,
                "metadata": metadata_json,
                "updated_at": datetime.utcnow(),
            },
        )
        db.commit()

        return LeadResponse(
            success=True,
            lead_id=lead_id,
            session_token=metadata["provisioning_token"],
            pricing=pricing,
            message="Lead updated successfully. Proceed to payment to create your account.",
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating lead: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update lead")
    finally:
        db.close()


@router.get("/{lead_id}")
async def get_lead(
    lead_id: str,
    authorization: Optional[str] = Header(default=None),
):
    """
    Get pre-tenant lead information by opaque ID plus provisioning token.
    """
    if not settings.DB_URL:
        raise HTTPException(status_code=500, detail="Database not configured")

    engine = create_engine(settings.DB_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        provisioning_token = _extract_bearer_token(authorization)
        lead = db.execute(
            text("""
                SELECT id, company_name, user_count, user_band, compliance_required,
                       package_name, estimated_price_cents, status, metadata, created_at, expires_at
                FROM leads
                WHERE id = :id
            """),
            {"id": lead_id}
        ).fetchone()

        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        _validate_provisioning_token(lead[8], provisioning_token)

        if lead[7] == "converted":
            raise HTTPException(status_code=404, detail="Lead not found")

        if lead[10] and lead[10] < datetime.utcnow():
            raise HTTPException(status_code=410, detail="Lead has expired")

        metadata = _coerce_lead_metadata(lead[8])
        plan_tier = derive_plan_tier(
            plan_tier=metadata.get("plan_tier"),
            package_name=lead[5],
            compliance_required=lead[4],
            services_selected=metadata.get("services_selected"),
        )

        return {
            "id": lead[0],
            "company_name": lead[1],
            "user_count": lead[2],
            "user_band": lead[3],
            "compliance_required": lead[4],
            "package_name": lead[5],
            "plan_tier": plan_tier,
            "estimated_price_cents": lead[6],
            "status": lead[7],
            "created_at": lead[9].isoformat() if lead[9] else None,
            "expires_at": lead[10].isoformat() if lead[10] else None,
            "has_active_checkout_session": lead[7] == "payment_started",
        }
    finally:
        db.close()
