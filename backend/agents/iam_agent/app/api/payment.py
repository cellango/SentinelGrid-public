"""
Payment API endpoints for handling Stripe payments.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, validator
from typing import Optional
import logging
import json
import hmac
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None
    logging.warning("stripe package not installed. Payment functionality will be limited to dev mode.")

from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.keycloak_admin_client import (
    KeycloakAdminClient,
    KeycloakAPIError,
    KeycloakUserExistsError,
)
from app.services.keycloak_admin_factory import build_keycloak_admin
from app.services.payment_service import PaymentService
from app.services.realm_manager import RealmManager
from sg_core.product_catalog import (
    derive_plan_tier,
    get_plan_display_name,
    normalize_plan_tier,
    requires_dedicated_realm,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/payment", tags=["payment"])

# Initialize Stripe (only if available and configured)
if STRIPE_AVAILABLE and settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY
elif not settings.PAYMENT_DEV_MODE:
    logger.warning("STRIPE_SECRET_KEY not set and PAYMENT_DEV_MODE is false. Payment functionality will be disabled.")


class CalculatePriceRequest(BaseModel):
    """Request to calculate pricing."""
    user_count: int
    compliance_required: bool = False
    plan_tier: Optional[str] = None
    billing_period: str = "monthly"  # monthly or yearly
    services_selected: Optional[dict] = None

    @validator("plan_tier")
    def validate_plan_tier(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = normalize_plan_tier(value)
        if normalized is None:
            raise ValueError("Invalid plan tier")
        return normalized


class CreateCheckoutSessionRequest(BaseModel):
    """Request to create Stripe checkout session."""
    lead_id: str  # Lead ID instead of tenant_id (account created after payment)
    provisioning_token: str
    billing_period: str = "monthly"
    success_url: str
    cancel_url: str
    services_selected: Optional[dict] = None


class PaymentSuccessRequest(BaseModel):
    """Request after successful payment."""
    session_id: str
    lead_id: str  # Lead ID to convert to account
    provisioning_token: str
    password: Optional[str] = None  # Optional password for dev mode (to avoid password reset)


class PentestCheckoutRequest(BaseModel):
    """One-time checkout for penetration testing engagements."""
    amount_cents: int
    currency: str = "usd"
    success_url: str
    cancel_url: str
    engagement_meta: Optional[dict] = None

    @validator("amount_cents")
    def validate_amount(cls, amount: int):
        if amount < 100:
            raise ValueError("Amount must be at least $1.00")
        return amount


def _coerce_lead_metadata(raw_metadata: object) -> dict:
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


def _validate_provisioning_token(lead_metadata: object, presented_token: str) -> None:
    stored_token = _coerce_lead_metadata(lead_metadata).get("provisioning_token")
    if not isinstance(stored_token, str) or not stored_token:
        raise HTTPException(status_code=403, detail="Invalid provisioning token")
    if not presented_token or not hmac.compare_digest(stored_token, presented_token):
        raise HTTPException(status_code=403, detail="Invalid provisioning token")


async def _provision_customer_admin_user(
    *,
    realm_name: str,
    lead: dict,
    tenant_id: str,
    customer_id: str,
    user_password: str,
    password_is_temporary: bool,
) -> bool:
    """Create or update the first tenant admin user in Keycloak."""
    required_actions = ["UPDATE_PASSWORD"] if password_is_temporary else []

    async with KeycloakAdminClient() as kc_admin:
        try:
            user_id = await kc_admin.create_user(
                realm=realm_name,
                username=lead["email"],
                email=lead["email"],
                first_name=lead["first_name"],
                last_name=lead["last_name"],
                enabled=True,
                email_verified=False,
                attributes={
                    "tenant_id": [tenant_id],
                    "customer_id": [customer_id],
                },
                required_actions=required_actions,
            )
        except KeycloakUserExistsError:
            existing_user = await kc_admin.get_user_by_username(realm_name, lead["email"], exact=True)
            if not existing_user:
                raise HTTPException(status_code=409, detail="User already exists in Keycloak")
            user_id = existing_user["id"]
            await kc_admin.update_user_attributes(
                realm_name,
                user_id,
                {
                    "tenant_id": [tenant_id],
                    "customer_id": [customer_id],
                },
            )
        except KeycloakAPIError as exc:
            raise HTTPException(status_code=502, detail=f"Keycloak user provisioning failed: {exc}") from exc

        try:
            await kc_admin.set_user_password(
                realm_name,
                user_id,
                user_password,
                temporary=password_is_temporary,
            )
            await kc_admin.assign_realm_role(realm_name, user_id, "TENANT_ADMIN")
            verified_user = await kc_admin.get_user_by_username(realm_name, lead["email"], exact=True)
        except KeycloakAPIError as exc:
            raise HTTPException(status_code=502, detail=f"Keycloak user provisioning failed: {exc}") from exc

    return verified_user is not None

@router.post("/calculate")
async def calculate_price(request: CalculatePriceRequest):
    """
    Calculate price based on package and user band.
    """
    try:
        pricing = PaymentService.calculate_price(
            user_count=request.user_count,
            compliance_required=request.compliance_required,
            plan_tier=request.plan_tier,
            billing_period=request.billing_period,
            services_selected=request.services_selected or {},
        )
        return pricing
    except Exception as e:
        logger.error(f"Error calculating price: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calculating price: {str(e)}")


@router.post("/create-checkout-session")
async def create_checkout_session(request: CreateCheckoutSessionRequest):
    """
    Create a Stripe checkout session for payment.
    Uses lead_id instead of tenant_id (account created after payment).
    In dev mode, bypasses Stripe and returns a mock session.
    """
    if not settings.DB_URL:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    engine = create_engine(settings.DB_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Get lead information
        lead = db.execute(
            text("""
                SELECT id, email, company_name, user_count, user_band, compliance_required,
                       package_name, estimated_price_cents, status, metadata, expires_at
                FROM leads
                WHERE id = :lead_id
            """),
            {"lead_id": request.lead_id}
        ).mappings().fetchone()
        
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        if lead["status"] == 'converted':
            raise HTTPException(status_code=400, detail="Lead already converted to account")

        if lead["expires_at"] and lead["expires_at"] < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Lead has expired")

        _validate_provisioning_token(lead.get("metadata"), request.provisioning_token)
        
        # Calculate current price from the canonical plan selection captured on the lead.
        lead_metadata = _coerce_lead_metadata(lead.get("metadata"))
        plan_tier = derive_plan_tier(
            plan_tier=lead_metadata.get("plan_tier"),
            package_name=lead.get("package_name"),
            compliance_required=lead.get("compliance_required", False),
            services_selected=lead_metadata.get("services_selected"),
        )
        services_selected = lead_metadata.get("services_selected") or request.services_selected or {}
        pricing = PaymentService.calculate_price(
            user_count=lead["user_count"],
            compliance_required=lead["compliance_required"],
            plan_tier=plan_tier,
            billing_period=request.billing_period,
            services_selected=services_selected,
        )
        
        if pricing.get("requires_sales_contact") or pricing.get("total") is None:
            raise HTTPException(
                status_code=400,
                detail="This package requires custom pricing. Please contact sales."
            )
        
        if pricing["total"] == 0:
            # Free tier - no payment needed (shouldn't happen with new model, but handle it)
            return {
                "session_id": None,
                "url": None,
                "free_tier": True,
                "message": "No payment required"
            }
        
        # Update lead status to payment_started
        db.execute(
            text("UPDATE leads SET status = 'payment_started', updated_at = :updated_at WHERE id = :lead_id"),
            {"lead_id": request.lead_id, "updated_at": datetime.utcnow()}
        )
        db.commit()
        
        # Dev mode: bypass Stripe
        if settings.PAYMENT_DEV_MODE:
            logger.info(f"DEV MODE: Bypassing Stripe checkout for lead {request.lead_id}")
            session_id = f"dev_session_{request.lead_id}"
            # Update lead with dev session ID
            db.execute(
                text("UPDATE leads SET stripe_session_id = :session_id WHERE id = :lead_id"),
                {"session_id": session_id, "lead_id": request.lead_id}
            )
            db.commit()
            return {
                "session_id": session_id,
                "url": f"{request.success_url.replace('{CHECKOUT_SESSION_ID}', session_id)}",
                "free_tier": False,
                "dev_mode": True
            }
        
        if not settings.STRIPE_SECRET_KEY:
            raise HTTPException(status_code=503, detail="Payment processing is not configured")
        
        if not STRIPE_AVAILABLE:
            raise HTTPException(status_code=503, detail="Stripe package not available")
        
        # Create Stripe checkout session
        package_display = get_plan_display_name(plan_tier)
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": package_display,
                        "description": f"Subscription for {lead['company_name']} ({lead['user_band']} users)"
                    },
                    "unit_amount": pricing["total"],
                    "recurring": {
                        "interval": "month" if request.billing_period == "monthly" else "year"
                    }
                },
                "quantity": 1
            }],
            mode="subscription",
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            customer_email=lead["email"],
            metadata={
                "lead_id": request.lead_id,
                "user_count": str(lead["user_count"]),
                "user_band": lead["user_band"],
                "package_name": plan_tier,
                "plan_tier": plan_tier,
                "billing_period": request.billing_period,
                "compliance_required": str(lead["compliance_required"])
            },
            allow_promotion_codes=True
        )
        
        # Update lead with Stripe session ID
        db.execute(
            text("UPDATE leads SET stripe_session_id = :session_id WHERE id = :lead_id"),
            {"session_id": checkout_session.id, "lead_id": request.lead_id}
        )
        db.commit()
        
        return {
            "session_id": checkout_session.id,
            "url": checkout_session.url,
            "free_tier": False
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating checkout session: {str(e)}")
    finally:
        db.close()


@router.post("/create-pentest-session")
async def create_pentest_checkout_session(request: PentestCheckoutRequest):
    """
    Create a one-time Stripe checkout for penetration testing.
    """
    if request.amount_cents < 100:
        raise HTTPException(status_code=400, detail="Amount must be at least $1.00")

    # Dev mode: bypass Stripe
    if settings.PAYMENT_DEV_MODE:
        session_id = f"dev_pentest_{int(datetime.utcnow().timestamp())}"
        return {
            "session_id": session_id,
            "url": request.success_url.replace("{CHECKOUT_SESSION_ID}", session_id),
            "free_tier": False,
            "dev_mode": True,
        }

    if not STRIPE_AVAILABLE or not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Payment processing is not configured")

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": (request.currency or "usd").lower(),
                        "product_data": {
                            "name": "Penetration Test (Web/API)",
                            "description": "One-time penetration testing engagement",
                        },
                        "unit_amount": request.amount_cents,
                    },
                    "quantity": 1,
                }
            ],
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            metadata={
                "engagement_type": "pentest",
                "test_meta": str(request.engagement_meta or {}),
            },
        )
        return {
            "session_id": checkout_session.id,
            "url": checkout_session.url,
            "free_tier": False,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating pentest checkout session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating checkout session: {str(e)}")


@router.post("/success")
async def payment_success(request: PaymentSuccessRequest):
    logger.info(f"💰 PAYMENT SUCCESS: Received request for lead {request.lead_id}, session {request.session_id}, password provided: {request.password is not None}")
    """
    Handle successful payment and create account from lead.
    This is called after Stripe redirects back to our success URL.
    In dev mode, bypasses Stripe verification.
    """
    if not settings.DB_URL:
        raise HTTPException(status_code=500, detail="Database not configured")
    
    engine = create_engine(settings.DB_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Get lead information
        lead = db.execute(
            text("""
                SELECT id, email, company_name, first_name, last_name, password_hash,
                       user_count, user_band, compliance_required, package_name,
                       estimated_price_cents, status, stripe_session_id, metadata, expires_at
                FROM leads
                WHERE id = :lead_id
            """),
            {"lead_id": request.lead_id}
        ).mappings().fetchone()
        
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        if lead["status"] == 'converted':
            raise HTTPException(status_code=400, detail="Lead already converted to account")

        if lead["expires_at"] and lead["expires_at"] < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Lead has expired")

        _validate_provisioning_token(lead.get("metadata"), request.provisioning_token)

        if lead["status"] != "payment_started":
            raise HTTPException(status_code=400, detail="Lead is not ready for payment completion")

        if not lead["stripe_session_id"] or lead["stripe_session_id"] != request.session_id:
            raise HTTPException(status_code=400, detail="Checkout session does not match lead")
        
        # Verify payment (dev mode or Stripe). For local/testing flows or when Stripe is not configured,
        # bypass Stripe and treat as paid.
        if settings.PAYMENT_DEV_MODE or not settings.STRIPE_SECRET_KEY or request.session_id.startswith("dev_session_"):
            logger.info(f"DEV/LOCAL MODE: Processing payment success for lead {request.lead_id}")
            billing_period = "monthly"
            payment_amount = int(lead["estimated_price_cents"]) if lead["estimated_price_cents"] is not None else 50000
            subscription_id = f"dev_sub_{request.lead_id}"
        else:
            # Production mode - verify with Stripe
            if not STRIPE_AVAILABLE:
                raise HTTPException(status_code=503, detail="Stripe package not available")
            
            try:
                # Retrieve checkout session from Stripe
                session = stripe.checkout.Session.retrieve(request.session_id)
                
                if session.payment_status != "paid":
                    raise HTTPException(status_code=400, detail="Payment not completed")
                
                # Verify this session belongs to this lead
                if session.metadata.get("lead_id") != request.lead_id:
                    raise HTTPException(status_code=400, detail="Session does not match lead")
                
                # Get billing period and amount from Stripe session
                billing_period = session.metadata.get("billing_period", "monthly")
                payment_amount = session.amount_total
                subscription_id = session.subscription
                
            except Exception as e:
                logger.error(f"Error retrieving Stripe session: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error verifying payment: {str(e)}")
        
        # Now create the account from the lead
        import uuid
        import re
        
        lead_metadata = _coerce_lead_metadata(lead.get("metadata"))
        services_selected = lead_metadata.get("services_selected") or {}
        plan_tier = derive_plan_tier(
            plan_tier=lead_metadata.get("plan_tier"),
            package_name=lead.get("package_name"),
            compliance_required=lead.get("compliance_required", False),
            services_selected=services_selected,
        )
        # Dedicated realm only if Comply is selected and the customer manages their own SOC handoff.
        realm_strategy = "shared"
        if requires_dedicated_realm(plan_tier, services_selected):
            realm_strategy = "dedicated"
        realm_name = "sentinelgrid"  # Default
        
        if realm_strategy == "dedicated":
            realm_manager = RealmManager(build_keycloak_admin(realm_name="master"))
            realm_name = realm_manager._generate_realm_name(lead["company_name"])
            realm_created = await realm_manager.create_dedicated_realm(
                realm_name,
                {"name": lead["company_name"], "package_name": plan_tier, "compliance_required": lead["compliance_required"]}
            )
            if not realm_created:
                raise HTTPException(status_code=502, detail="Failed to provision dedicated Keycloak realm")
        
        # Create customer and tenant
        customer_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        
        # Generate unique slug
        base_slug = (lead_metadata.get("tenant_slug") or lead["company_name"]).lower().replace(" ", "-").replace("_", "-")
        base_slug = re.sub(r'[^a-z0-9-]', '', base_slug)
        if not base_slug:
            base_slug = "tenant"
        
        existing_tenant = db.execute(
            text("SELECT id FROM tenants WHERE slug = :slug"),
            {"slug": base_slug}
        ).fetchone()
        
        slug = f"{base_slug}-{str(tenant_id)[:8]}" if existing_tenant else base_slug
        
        # Create customer record with new fields (must exist before tenant due to FK)
        db.execute(
            text("""
                INSERT INTO customers (
                    id, name, realm_name, has_dedicated_realm, package_name, plan_tier, user_band, user_count,
                    compliance_required, payment_status, billing_period, stripe_subscription_id,
                    subscription_start_date, subscription_end_date, next_payment_date, last_payment_date,
                    payment_amount_cents, currency, signup_completed, created_at, updated_at
                )
                VALUES (
                    :id, :name, :realm_name, :has_dedicated_realm, :package_name, :plan_tier, :user_band, :user_count,
                    :compliance_required, 'paid', :billing_period, :subscription_id,
                    :start_date, :end_date, :next_payment, :last_payment,
                    :amount, 'usd', False, :created_at, :updated_at
                )
            """),
            {
                "id": customer_id,
                "name": lead["company_name"],
                "realm_name": realm_name if realm_strategy == "dedicated" else None,
                "has_dedicated_realm": realm_strategy == "dedicated",
                "package_name": plan_tier,
                "plan_tier": plan_tier,
                "user_band": lead["user_band"],
                "user_count": lead["user_count"],
                "compliance_required": lead["compliance_required"],
                "billing_period": billing_period,
                "subscription_id": subscription_id,
                "start_date": datetime.utcnow(),
                "end_date": datetime.utcnow() + (timedelta(days=365) if billing_period == "yearly" else timedelta(days=30)),
                "next_payment": datetime.utcnow() + (timedelta(days=365) if billing_period == "yearly" else timedelta(days=30)),
                "last_payment": datetime.utcnow(),
                "amount": payment_amount,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        )

        # Create tenant after customer exists to satisfy FK
        db.execute(
            text("""
                INSERT INTO tenants (
                    id, name, slug, status, customer_id, package_name, plan_tier,
                    incident_management_mode, ticketing_provider, ticketing_project, services_selected,
                    created_at, updated_at
                )
                VALUES (
                    :id, :name, :slug, :status, :customer_id, :package_name, :plan_tier,
                    :incident_management_mode, :ticketing_provider, :ticketing_project, CAST(:services_selected AS jsonb),
                    :created_at, :updated_at
                )
            """),
            {
                "id": tenant_id,
                "name": lead["company_name"],
                "slug": slug,
                "status": "active",
                "customer_id": customer_id,
                "package_name": plan_tier,
                "plan_tier": plan_tier,
                "incident_management_mode": "saas_managed" if services_selected.get("socManaged") is not False else "customer_managed",
                "ticketing_provider": services_selected.get("ticketing") or "internal",
                "ticketing_project": services_selected.get("ticketingProject"),
                "services_selected": json.dumps(services_selected),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        )
        
        # Create user in Keycloak
        # Get password from lead (stored as hash, but we need to verify it was stored correctly)
        # Note: In production, we'd need to store the password differently or use a different approach
        # For now, we'll need to get the password from the lead creation - but that's not ideal
        # TODO: Consider storing password in encrypted form or using a different flow
        
        # For now, we'll create the user and they'll need to reset password
        # Or we can store password temporarily in a secure way during lead creation
        # Actually, let's check if we can retrieve the password from the lead's password_hash
        # We can't decrypt bcrypt, so we need a different approach
        
        # Use provided password if available (dev mode), otherwise use temporary password
        user_password = request.password if request.password else "TempPassword123!"
        password_is_temporary = request.password is None
        logger.info(f"🔐 Password configuration for user {lead['email']}: temporary={password_is_temporary}, password_provided={request.password is not None}, password_length={len(user_password) if user_password else 0}")
        
        user_verified_final = await _provision_customer_admin_user(
            realm_name=realm_name,
            lead=lead,
            tenant_id=tenant_id,
            customer_id=customer_id,
            user_password=user_password,
            password_is_temporary=password_is_temporary,
        )
        
        # Mark lead as converted
        db.execute(
            text("""
                UPDATE leads 
                SET status = 'converted',
                    converted_at = :converted_at,
                    converted_to_tenant_id = :tenant_id,
                    converted_to_customer_id = :customer_id,
                    updated_at = :updated_at
                WHERE id = :lead_id
            """),
            {
                "lead_id": request.lead_id,
                "converted_at": datetime.utcnow(),
                "tenant_id": tenant_id,
                "customer_id": customer_id,
                "updated_at": datetime.utcnow()
            }
        )
        
        db.commit()
        
        logger.info(
            "✅ Account created from lead %s: tenant %s, customer %s, realm %s, user_verified=%s",
            request.lead_id,
            tenant_id,
            customer_id,
            realm_name,
            user_verified_final,
        )
        
        return {
            "success": True,
            "message": "Payment processed and account created successfully" + (" (DEV MODE)" if settings.PAYMENT_DEV_MODE else ""),
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "subscription_id": subscription_id,
            "email": lead["email"],
            "dev_mode": settings.PAYMENT_DEV_MODE,
            "password_reset_required": password_is_temporary,  # Only require reset if using temporary password
            "user_verified": user_verified_final  # Whether user was verified in Keycloak
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing payment success: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing payment: {str(e)}")
    finally:
        db.close()


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events (for subscription updates, cancellations, etc.)
    In dev mode, webhooks are disabled.
    """
    if settings.PAYMENT_DEV_MODE:
        logger.info("DEV MODE: Webhook received but ignored")
        return {"status": "success", "dev_mode": True, "message": "Webhook ignored in dev mode"}
    
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")
    
    if not STRIPE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Stripe package not available")
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle different event types
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        logger.info(f"Checkout session completed: {session.id}")
        # Payment success handler will update the database
        
    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        logger.info(f"Subscription updated: {subscription.id}")
        # Update subscription in database
        
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        logger.info(f"Subscription cancelled: {subscription.id}")
        # Mark subscription as cancelled in database
        
    return {"status": "success"}
