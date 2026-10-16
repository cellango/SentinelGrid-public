"""Tenant provisioning service."""

import logging
from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.keycloak import KeycloakAdminClient
from app.models.tenant import TenantProvisionRequest, TenantProvisionResponse
from app.core.config import settings

logger = logging.getLogger(__name__)


class ProvisioningService:
    """Service for tenant provisioning."""
    
    def __init__(self, db: Session, keycloak_client: KeycloakAdminClient):
        self.db = db
        self.keycloak = keycloak_client
    
    def provision_tenant(self, request: TenantProvisionRequest) -> TenantProvisionResponse:
        """
        Provision a new tenant.
        
        Steps:
        1. Generate tenant UUID
        2. Create database record
        3. Create Keycloak realm
        4. Create Keycloak clients
        5. Create admin user
        6. Assign roles
        7. Configure protocol mappers
        
        Args:
            request: Provisioning request
        
        Returns:
            Provisioning response with tenant details
        """
        tenant_id = uuid4()
        realm_name = request.slug
        admin_username = request.admin_email
        
        try:
            # Step 1: Create database tenant record
            logger.info(f"Creating tenant record in database: {tenant_id}")
            self.db.execute(
                text("""
                    INSERT INTO tenants (id, name, slug, status, created_at, updated_at)
                    VALUES (:id, :name, :slug, :status, :created_at, :updated_at)
                """),
                {
                    "id": str(tenant_id),
                    "name": request.company_name,
                    "slug": realm_name,
                    "status": "active",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            )
            self.db.commit()
            
            # Step 2: Create Keycloak realm
            logger.info(f"Creating Keycloak realm: {realm_name}")
            self.keycloak.create_realm(
                realm_name=realm_name,
                enabled=True,
                display_name=request.company_name
            )
            
            # Step 3: Create clients (web and api)
            logger.info(f"Creating clients for realm: {realm_name}")
            self.keycloak.create_client(
                realm_name=realm_name,
                client_id=f"{realm_name}-web",
                client_type="public",
                redirect_uris=["http://localhost:3000/*", "https://*.sentinelgrid.com/*"]
            )
            
            self.keycloak.create_client(
                realm_name=realm_name,
                client_id=f"{realm_name}-api",
                client_type="confidential",
                redirect_uris=[]
            )
            
            # Step 4: Create admin user
            logger.info(f"Creating admin user: {admin_username}")
            user_id = self.keycloak.create_user(
                realm_name=realm_name,
                username=admin_username,
                email=request.admin_email,
                password=request.admin_password,
                first_name=request.admin_first_name,
                last_name=request.admin_last_name,
                enabled=True,
                email_verified=True
            )
            
            # Step 5: Set tenant_id attribute on user
            try:
                self.keycloak.update_user_attributes(
                    realm_name=realm_name,
                    user_id=user_id,
                    attributes={
                        "tenant_id": [str(tenant_id)],
                    },
                )
                logger.info(f"Set tenant_id attribute on user {user_id}")
            except Exception as e:
                logger.warning(f"Could not set tenant_id attribute: {e}")
            
            # Step 6: Create and assign TENANT_ADMIN role
            try:
                self.keycloak.assign_role(
                    realm_name=realm_name,
                    user_id=user_id,
                    role_name="TENANT_ADMIN"
                )
            except Exception as e:
                logger.warning(f"Could not assign TENANT_ADMIN role: {e}")
            
            # Step 7: Add tenant_id protocol mapper to API client
            try:
                self.keycloak.add_tenant_id_mapper(
                    realm_name=realm_name,
                    client_id=f"{realm_name}-api"
                )
            except Exception as e:
                logger.warning(f"Could not add tenant_id mapper: {e}")
            
            logger.info(f"Successfully provisioned tenant: {tenant_id}")
            
            return TenantProvisionResponse(
                tenant_id=tenant_id,
                realm_name=realm_name,
                company_name=request.company_name,
                admin_username=admin_username,
                admin_email=request.admin_email,
                status="active",
                created_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Failed to provision tenant: {e}")
            self.db.rollback()
            # Attempt cleanup
            try:
                # Delete from database if created
                self.db.execute(
                    text("DELETE FROM tenants WHERE id = :id"),
                    {"id": str(tenant_id)}
                )
                self.db.commit()
            except:
                pass
            raise
