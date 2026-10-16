"""
Enhanced Tenant Provisioning Service - Realm-aware provisioning.
Integrates with multi-tenant realm architecture, region support, and pricing tiers.
"""

import logging
import json
from uuid import uuid4
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from keycloak import KeycloakAdmin

# Import existing services
import sys

# Ensure IAM agent code is importable (for pricing/realm helpers)
sys.path.insert(0, "/app/agents/iam_agent/app")
sys.path.insert(0, "/app/agents/iam_agent")

from services.pricing_service import PricingService
from services.realm_manager import RealmManager
from services.multi_tenant_realm_manager import MultiTenantRealmManager
from sg_core.product_catalog import (
    apply_plan_defaults,
    derive_plan_tier,
    plan_includes_compliance,
    requires_dedicated_realm,
)

logger = logging.getLogger(__name__)


class EnhancedProvisioningService:
    """
    Enhanced provisioning service with full realm architecture support.
    
    Handles:
    - Pricing tier determination
    - Realm strategy selection (shared vs dedicated)
    - Region-based realm assignment
    - Customer and organization creation
    - Keycloak user provisioning with proper attributes
    """
    
    def __init__(
        self,
        db_session: Session,
        keycloak_admin: KeycloakAdmin
    ):
        """
        Initialize enhanced provisioning service.
        
        Args:
            db_session: SQLAlchemy database session
            keycloak_admin: KeycloakAdmin instance (master realm)
        """
        self.db = db_session
        self.keycloak = keycloak_admin
        self.realm_manager = RealmManager(keycloak_admin)
        self.mt_realm_manager = MultiTenantRealmManager(keycloak_admin, db_session)
    
    def provision_tenant(
        self,
        company_name: str,
        admin_email: str,
        admin_password: str,
        admin_first_name: str,
        admin_last_name: str,
        employee_count: Optional[int] = None,
        region: str = "us",
        compliance_required: bool = False,
        industry: Optional[str] = None,
        tenant_slug: Optional[str] = None,
        services_selected: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Provision a new tenant with full realm architecture support.
        
        Args:
            company_name: Company name
            admin_email: Admin user email
            admin_password: Admin user password
            admin_first_name: Admin first name
            admin_last_name: Admin last name
            employee_count: Number of employees (for tier determination)
            region: Region code (us, eu, ap, etc.)
            compliance_required: Whether compliance mandates dedicated realm
            industry: Industry (optional, for analytics)
        
        Returns:
            Dict with provisioning results
        """
        customer_created = False
        tenant_created = False
        realm_name = None
        try:
            logger.info(f"🚀 Starting tenant provisioning for {company_name}")
            
            # Step 1: Generate IDs and slug
            customer_id = uuid4()
            tenant_id = uuid4()
            slug = self._generate_slug(company_name, preferred=tenant_slug)
            org_data: Optional[Dict[str, Any]] = None
            services = apply_plan_defaults(
                derive_plan_tier(
                    compliance_required=compliance_required,
                    services_selected=services_selected,
                ),
                services_selected,
            )
            
            # Step 2: Determine pricing tier
            pricing_tier = self._determine_pricing_tier(employee_count)
            logger.info(f"📊 Determined pricing tier: {pricing_tier}")

            # Step 2b: Determine plan tier (Protect / Protect & Defend / Protect, Defend & Comply)
            plan_tier = derive_plan_tier(
                compliance_required=compliance_required,
                services_selected=services
            )
            logger.info(f"📦 Plan tier: {plan_tier}")
            
            # Step 3: Determine realm strategy
            realm_strategy = PricingService.get_realm_strategy(
                pricing_tier=pricing_tier,
                user_count=1,  # Starting with admin user
                org_count=0
            )

            # Incident/ticketing preferences from signup
            incident_management_mode = "saas_managed" if services_selected is None else (
                "saas_managed" if services.get("socManaged") else "customer_managed"
            )
            ticketing_provider = services.get("ticketing") or "internal"
            ticketing_project = services.get("ticketingProject")
            
            # Override for compliance
            if plan_includes_compliance(plan_tier):
                realm_strategy = "dedicated"
                logger.info("🔒 Compliance required - forcing dedicated realm")
            
            logger.info(f"🏛️  Realm strategy: {realm_strategy}")
            
            # Step 4: Create customer record
            customer_data = self._create_customer(
                customer_id=customer_id,
                name=company_name,
                slug=slug,
                pricing_tier=pricing_tier,
                plan_tier=plan_tier,
                region=region,
                compliance_required=compliance_required,
                employee_count=employee_count,
                industry=industry,
                realm_strategy=realm_strategy
            )
            customer_created = True

            # Log provisioning start now that the customer row exists (avoids FK errors)
            self._log_provisioning_event(
                tenant_id=None,  # tenant row not created yet
                customer_id=customer_id,
                event_type="provision_start",
                details={"company_name": company_name, "region": region, "slug": slug}
            )
            
            # Step 5: Assign or create realm
            # Override for SOC-as-a-Service (managed incidents)
            if requires_dedicated_realm(plan_tier, services):
                realm_strategy = "dedicated"
                logger.info("🔒 Comply tier with customer-managed handoff - forcing dedicated realm")

            if realm_strategy == "shared":
                realm_name, org_data = self._assign_shared_realm(region, tenant_id, slug, customer_id)
            else:
                realm_name = self._create_dedicated_realm(slug, customer_id, company_name)
            logger.info(f"🏛️  Assigned realm: {realm_name}")
            
            # Update customer with realm name
            self.db.execute(
                text("""
                    UPDATE customers
                    SET realm_name = :realm_name,
                        has_dedicated_realm = :has_dedicated,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :customer_id
                """),
                {
                    "realm_name": realm_name,
                    "has_dedicated": realm_strategy == "dedicated",
                    "customer_id": str(customer_id)
                }
            )
            self.db.commit()
            
            # Step 6: Create tenant record
            tenant_data = self._create_tenant(
                tenant_id=tenant_id,
                customer_id=customer_id,
                name=company_name,
                slug=slug,
                realm_name=realm_name,
                region=region,
                pricing_tier=pricing_tier,
                plan_tier=plan_tier,
                realm_strategy=realm_strategy,
                incident_management_mode=incident_management_mode,
                ticketing_provider=ticketing_provider,
                ticketing_project=ticketing_project,
                services_selected=services,
            )
            tenant_created = True

            # Persist org/group references now that the tenant row exists
            if org_data:
                self.db.execute(
                    text("""
                        UPDATE tenants
                        SET keycloak_org_id = :org_id,
                            keycloak_group_id = :group_id
                        WHERE id = :tenant_id
                    """),
                    {
                        "org_id": org_data.get("keycloak_org_id"),
                        "group_id": org_data.get("keycloak_group_id"),
                        "tenant_id": str(tenant_id)
                    }
                )
                self.db.commit()

            # Log realm assignment after tenant exists to satisfy FKs
            self._log_provisioning_event(
                tenant_id=tenant_id,
                customer_id=customer_id,
                event_type="realm_assigned",
                realm_name=realm_name,
                details={"realm_type": realm_strategy, "org_data": org_data if realm_strategy == "shared" else None}
            )
            
            # Step 7: Create admin user in Keycloak
            user_id = self._create_admin_user(
                realm_name=realm_name,
                tenant_id=tenant_id,
                customer_id=customer_id,
                slug=slug,
                email=admin_email,
                password=admin_password,
                first_name=admin_first_name,
                last_name=admin_last_name
            )
            
            logger.info(f"👤 Created admin user: {admin_email} (ID: {user_id})")
            
            # Step 8: Assign roles
            self._assign_roles(realm_name, user_id, ["TENANT_ADMIN"])
            
            # Log success
            self._log_provisioning_event(
                tenant_id=tenant_id,
                customer_id=customer_id,
                event_type="provision_success",
                realm_name=realm_name,
                details={
                "realm_name": realm_name,
                "realm_strategy": realm_strategy,
                "pricing_tier": pricing_tier,
                "plan_tier": plan_tier,
                "admin_user_id": user_id
            }
            )
            
            logger.info(f"✅ Successfully provisioned tenant: {company_name}")
            
            return {
                "success": True,
                "tenant_id": str(tenant_id),
                "customer_id": str(customer_id),
                "realm_name": realm_name,
                "realm_strategy": realm_strategy,
                "pricing_tier": pricing_tier,
                "plan_tier": plan_tier,
                "slug": slug,
                "admin_email": admin_email,
                "region": region,
                "created_at": datetime.utcnow().isoformat(),
                "services_selected": services or {},
                "incident_management_mode": incident_management_mode,
                "ticketing_provider": ticketing_provider,
            }
            
        except Exception as e:
            logger.error(f"❌ Tenant provisioning failed: {e}", exc_info=True)
            
            # Log failure
            try:
                self._log_provisioning_event(
                    tenant_id=tenant_id if tenant_created else None,
                    customer_id=customer_id if customer_created else None,
                    event_type="provision_failure",
                    error_message=str(e)
                )
            except:
                pass
            
            # Rollback database changes
            self.db.rollback()
            
            raise
    
    def _determine_pricing_tier(self, employee_count: Optional[int]) -> str:
        """
        Determine pricing tier based on employee count.
        
        Args:
            employee_count: Number of employees
        
        Returns:
            Pricing tier (free, starter, professional, enterprise)
        """
        if employee_count is None:
            return "starter"  # Default
        
        return PricingService.determine_tier_from_employee_count(employee_count)

    def _generate_slug(self, company_name: str, preferred: Optional[str] = None) -> str:
        """
        Generate URL-safe slug from company name.
        
        Args:
            company_name: Company name
        
        Returns:
            Slug
        """
        import re
        base_input = preferred or company_name
        slug = base_input.lower().replace(" ", "-").replace("_", "-")
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip("-")

        # Enforce length/pattern
        if len(slug) < 3:
            slug = slug.ljust(3, 'x')
        if len(slug) > 40:
            slug = slug[:40]
        if slug.startswith('-') or slug.endswith('-') or '--' in slug:
            slug = re.sub(r'-+', '-', slug.strip('-'))

        # Ensure uniqueness
        base_slug = slug
        counter = 1
        while self._slug_exists(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    def _slug_exists(self, slug: str) -> bool:
        """Check if slug already exists."""
        result = self.db.execute(
            text("SELECT 1 FROM customers WHERE slug = :slug LIMIT 1"),
            {"slug": slug}
        ).first()
        if result:
            return True
        result = self.db.execute(
            text("SELECT 1 FROM tenants WHERE slug = :slug LIMIT 1"),
            {"slug": slug}
        ).first()
        return result is not None
    
    def _create_customer(
        self,
        customer_id: uuid4,
        name: str,
        slug: str,
        pricing_tier: str,
        plan_tier: str,
        region: str,
        compliance_required: bool,
        employee_count: Optional[int],
        industry: Optional[str],
        realm_strategy: str
    ) -> Dict[str, Any]:
        """Create customer record in database."""
        self.db.execute(
            text("""
                INSERT INTO customers (
                    id, name, slug, pricing_tier, plan_tier, region, compliance_required,
                    employee_count, industry, has_dedicated_realm, user_count, org_count, status
                )
                VALUES (
                    :id, :name, :slug, :pricing_tier, :plan_tier, :region, :compliance_required,
                    :employee_count, :industry, :has_dedicated_realm, 0, 0, 'active'
                )
            """),
            {
                "id": str(customer_id),
                "name": name,
                "slug": slug,
                "pricing_tier": pricing_tier,
                "plan_tier": plan_tier,
                "region": region,
                "compliance_required": compliance_required,
                "employee_count": employee_count,
                "industry": industry,
                "has_dedicated_realm": realm_strategy == "dedicated"
            }
        )
        self.db.commit()
        
        logger.info(f"✅ Created customer record: {name} (ID: {customer_id})")
        
        return {
            "id": str(customer_id),
            "name": name,
            "slug": slug,
            "pricing_tier": pricing_tier,
            "plan_tier": plan_tier
        }
    
    def _assign_shared_realm(
        self,
        region: str,
        tenant_id: uuid4,
        slug: str,
        customer_id: uuid4
    ) -> tuple[str, Dict[str, Any]]:
        """
        Assign tenant to a shared multi-tenant realm.
        
        Args:
            region: Region code
            tenant_id: Tenant UUID
            slug: Tenant slug
            customer_id: Customer UUID
        
        Returns:
            Tuple of realm name and organization/group metadata
        """
        # Get available shared realm in region
        realm_name = self.mt_realm_manager.get_available_shared_realm(region)
        
        # Create organization or group for tenant isolation
        org_data = self.mt_realm_manager.assign_tenant_to_shared_realm(
            tenant_id=str(tenant_id),
            tenant_slug=slug,
            realm_name=realm_name,
            customer_id=str(customer_id)
        )
        
        return realm_name, org_data
    
    def _create_dedicated_realm(
        self,
        slug: str,
        customer_id: uuid4,
        company_name: str
    ) -> str:
        """
        Create dedicated enterprise realm.
        
        Args:
            slug: Customer slug
            customer_id: Customer UUID
            company_name: Company name
        
        Returns:
            Realm name
        """
        realm_name = f"sg-ent-{slug}"
        
        # Create realm using RealmManager
        success = self.realm_manager.create_dedicated_realm(
            realm_name=realm_name,
            customer_data={"name": company_name},
            organization_data=None
        )
        
        if not success:
            raise Exception(f"Failed to create dedicated realm: {realm_name}")
        
        # Register realm in database
        self.db.execute(
            text("""
                INSERT INTO realms (realm_name, realm_type, region, status, tenant_count, max_tenants)
                VALUES (:realm_name, 'enterprise', :region, 'active', 0, NULL)
                ON CONFLICT (realm_name) DO UPDATE
                SET updated_at = now()
            """),
            {
                "realm_name": realm_name,
                "region": "us"  # Default region for enterprise
            }
        )
        self.db.commit()
        
        self._log_provisioning_event(
            tenant_id=None,
            customer_id=customer_id,
            event_type="realm_assigned",
            realm_name=realm_name,
            details={"realm_type": "dedicated"}
        )
        
        return realm_name
    
    def _create_tenant(
        self,
        tenant_id: uuid4,
        customer_id: uuid4,
        name: str,
        slug: str,
        realm_name: str,
        region: str,
        pricing_tier: str,
        plan_tier: str,
        realm_strategy: str,
        incident_management_mode: str = "saas_managed",
        ticketing_provider: str = "internal",
        ticketing_project: Optional[str] = None,
        services_selected: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create tenant record in database."""
        services_selected_json = json.dumps(services_selected) if services_selected is not None else None
        self.db.execute(
            text("""
                INSERT INTO tenants (
                    id, customer_id, name, slug, realm_name, region,
                    pricing_tier, plan_tier, realm_strategy, incident_management_mode,
                    ticketing_provider, ticketing_project, services_selected,
                    status
                )
                VALUES (
                    :id, :customer_id, :name, :slug, :realm_name, :region,
                    :pricing_tier, :plan_tier, :realm_strategy, :incident_management_mode,
                    :ticketing_provider, :ticketing_project, :services_selected,
                    'active'
                )
            """),
            {
                "id": str(tenant_id),
                "customer_id": str(customer_id),
                "name": name,
                "slug": slug,
                "realm_name": realm_name,
                "region": region,
                "pricing_tier": pricing_tier,
                "plan_tier": plan_tier,
                "realm_strategy": realm_strategy,
                "incident_management_mode": incident_management_mode,
                "ticketing_provider": ticketing_provider,
                "ticketing_project": ticketing_project,
                "services_selected": services_selected_json,
            }
        )
        self.db.commit()
        
        logger.info(f"✅ Created tenant record: {name} (ID: {tenant_id})")
        
        return {
            "id": str(tenant_id),
            "name": name,
            "slug": slug,
            "realm_name": realm_name
        }
    
    def _create_admin_user(
        self,
        realm_name: str,
        tenant_id: uuid4,
        customer_id: uuid4,
        slug: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str
    ) -> str:
        """
        Create admin user in Keycloak with proper attributes.
        
        Args:
            realm_name: Realm name
            tenant_id: Tenant UUID
            customer_id: Customer UUID
            slug: Tenant slug
            email: User email
            password: User password
            first_name: First name
            last_name: Last name
        
        Returns:
            User ID
        """
        # Switch to target realm
        original_realm = self.keycloak.realm_name
        self.keycloak.realm_name = realm_name
        
        try:
            # Create user
            user_data = {
                "username": email,
                "email": email,
                "firstName": first_name,
                "lastName": last_name,
                "enabled": True,
                "emailVerified": True,
                "attributes": {
                    "tenant_id": [str(tenant_id)],
                    "tenant_slug": [slug],
                    "customer_id": [str(customer_id)],
                }
            }
            
            user_id = self.keycloak.create_user(user_data)
            
            # Set password
            self.keycloak.set_user_password(user_id, password, temporary=False)
            
            logger.info(f"✅ Created user in Keycloak: {email}")
            
            self._log_provisioning_event(
                tenant_id=tenant_id,
                customer_id=customer_id,
                event_type="user_created",
                realm_name=realm_name,
                details={"user_id": user_id, "email": email}
            )
            
            return user_id
            
        finally:
            self.keycloak.realm_name = original_realm
    
    def _assign_roles(self, realm_name: str, user_id: str, roles: list):
        """Assign roles to user."""
        original_realm = self.keycloak.realm_name
        self.keycloak.realm_name = realm_name
        
        try:
            for role_name in roles:
                try:
                    role = self.keycloak.get_realm_role(role_name)
                    self.keycloak.assign_realm_roles(user_id, [role])
                    logger.info(f"✅ Assigned role {role_name} to user")
                except Exception as e:
                    logger.warning(f"Could not assign role {role_name}: {e}")
        finally:
            self.keycloak.realm_name = original_realm
    
    def _log_provisioning_event(
        self,
        tenant_id: Optional[uuid4],
        customer_id: Optional[uuid4],
        event_type: str,
        realm_name: Optional[str] = None,
        details: Optional[Dict] = None,
        error_message: Optional[str] = None
    ):
        """Log provisioning event to audit table."""
        try:
            import json
            self.db.execute(
                text("""
                    INSERT INTO tenant_provisioning_log (
                        tenant_id, customer_id, event_type, realm_name, details, error_message
                    )
                    VALUES (:tenant_id, :customer_id, :event_type, :realm_name, :details, :error_message)
                """),
                {
                    "tenant_id": str(tenant_id) if tenant_id else None,
                    "customer_id": str(customer_id) if customer_id else None,
                    "event_type": event_type,
                    "realm_name": realm_name,
                    "details": json.dumps(details) if details else None,
                    "error_message": error_message
                }
            )
            self.db.commit()
        except Exception as e:
            logger.warning(f"Could not log provisioning event: {e}")
            try:
                self.db.rollback()
            except Exception:
                pass
