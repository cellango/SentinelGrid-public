"""Tenant provisioning API endpoints."""

import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_current_tenant, get_db, get_tenant_session
from app.core.keycloak import KeycloakAdminClient
from app.models.tenant import (
    TenantProvisionRequest, 
    TenantProvisionResponse,
    IntegrationStatus,
    IdentityProviderStatus,
    CloudProviderStatus,
    AlertPreferencesRequest,
    AlertPreferencesResponse,
    FeatureFlagsRequest,
    FeatureFlagsResponse,
    UserInvitationRequest,
    UserInvitationResponse
)
from app.services.provisioning_service import ProvisioningService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/tenants", tags=["tenants"])


def _enforce_same_tenant(path_tenant_id: UUID, current_tenant_id: UUID) -> None:
    if str(path_tenant_id) != str(current_tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access denied",
        )


def _ensure_tenant_preferences_table(db: Session) -> None:
    """Create tenant preferences table using the active database dialect."""
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        ddl = """
            CREATE TABLE IF NOT EXISTS tenant_preferences (
                tenant_id TEXT PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
                alert_preferences TEXT NOT NULL DEFAULT '{}',
                feature_flags TEXT NOT NULL DEFAULT '{}',
                notification_email TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """
    else:
        ddl = """
            CREATE TABLE IF NOT EXISTS tenant_preferences (
                tenant_id UUID PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
                alert_preferences JSONB NOT NULL DEFAULT '{}',
                feature_flags JSONB NOT NULL DEFAULT '{}',
                notification_email TEXT,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """

    db.execute(text(ddl))
    db.commit()


def _json_bind(name: str, db: Session) -> str:
    """Return the correct bind expression for JSON payloads on the active dialect."""
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        return f":{name}"
    return f":{name}::jsonb"


def get_keycloak_client() -> KeycloakAdminClient:
    """Dependency to get Keycloak admin client."""
    return KeycloakAdminClient()


def get_provisioning_service(
    db: Session = Depends(get_db),
    keycloak_client: KeycloakAdminClient = Depends(get_keycloak_client)
) -> ProvisioningService:
    """Dependency to get provisioning service."""
    return ProvisioningService(db, keycloak_client)


@router.post("/provision", response_model=TenantProvisionResponse, status_code=status.HTTP_201_CREATED)
def provision_tenant(
    request: TenantProvisionRequest,
    service: ProvisioningService = Depends(get_provisioning_service)
):
    """
    Provision a new tenant.
    
    This endpoint:
    1. Creates a tenant record in the database
    2. Creates a Keycloak realm
    3. Creates Keycloak clients (web, api)
    4. Creates admin user
    5. Assigns roles
    6. Configures protocol mappers
    
    **Note:** This is a privileged operation. In production, add authentication/authorization.
    """
    try:
        result = service.provision_tenant(request)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to provision tenant: {str(e)}"
        )


@router.get("/{tenant_id}/integration-status", response_model=IntegrationStatus)
def get_integration_status(
    tenant_id: UUID,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """
    Get integration status for a tenant.
    
    Returns the status of:
    - Identity provider connections (Google Workspace, Microsoft 365, Okta)
    - Cloud provider connections (AWS, Azure, GCP)
    """
    try:
        _enforce_same_tenant(tenant_id, current_tenant_id)
        # Check if tenant exists
        tenant_result = db.execute(
            text("SELECT id FROM tenants WHERE id = :tenant_id"),
            {"tenant_id": str(tenant_id)}
        ).first()
        
        if not tenant_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found"
            )
        
        # Query identity provider connectors
        idp_connectors = db.execute(
            text("""
                SELECT type, status, last_sync_at, error_message
                FROM connector_configs
                WHERE tenant_id = :tenant_id
                AND type IN ('google_workspace', 'microsoft_entra', 'okta')
                AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"tenant_id": str(tenant_id)}
        ).first()
        
        identity_provider = None
        if idp_connectors:
            # Try to get user count from connector (if available in credentials/config)
            # For now, we'll just return the status
            identity_provider = {
                "provider": idp_connectors[0],
                "status": "connected" if idp_connectors[1] == "active" else "error",
                "last_sync": idp_connectors[2].isoformat() if idp_connectors[2] else None,
                "error_message": idp_connectors[3]
            }
        else:
            identity_provider = {
                "provider": "sentinelgrid",  # Default to SentinelGrid if no external IdP
                "status": "connected",
                "last_sync": None,
                "error_message": None
            }
        
        # Query cloud provider connectors
        cloud_connectors = db.execute(
            text("""
                SELECT type, status, last_sync_at, error_message
                FROM connector_configs
                WHERE tenant_id = :tenant_id
                AND type IN ('aws', 'azure', 'gcp')
                AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"tenant_id": str(tenant_id)}
        ).first()
        
        cloud_provider = None
        if cloud_connectors:
            cloud_provider = {
                "provider": cloud_connectors[0],
                "status": "connected" if cloud_connectors[1] == "active" else "error",
                "last_events": cloud_connectors[2].isoformat() if cloud_connectors[2] else None,
                "error_message": cloud_connectors[3]
            }
        else:
            cloud_provider = {
                "provider": None,
                "status": "not_connected",
                "last_events": None,
                "error_message": None
            }
        
        return IntegrationStatus(
            identity_provider=identity_provider,
            cloud_provider=cloud_provider
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get integration status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get integration status: {str(e)}"
        )


@router.post("/{tenant_id}/alert-preferences", response_model=AlertPreferencesResponse)
def set_alert_preferences(
    tenant_id: UUID,
    request: AlertPreferencesRequest,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """
    Set alert preferences for a tenant.
    
    Stores email notification preferences and notification email address.
    """
    try:
        _enforce_same_tenant(tenant_id, current_tenant_id)
        # Check if tenant exists
        tenant_result = db.execute(
            text("SELECT id FROM tenants WHERE id = :tenant_id"),
            {"tenant_id": str(tenant_id)}
        ).first()
        
        if not tenant_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found"
            )
        
        # Check if alert preferences table exists, if not create it
        # For now, we'll use a simple JSONB column in tenants table or create a separate table
        # Let's create a tenant_preferences table if it doesn't exist
        _ensure_tenant_preferences_table(db)
        
        # Upsert alert preferences
        now = datetime.utcnow()
        alert_preferences_bind = _json_bind("alert_preferences", db)
        db.execute(
            text(f"""
                INSERT INTO tenant_preferences (tenant_id, alert_preferences, notification_email, updated_at)
                VALUES (:tenant_id, {alert_preferences_bind}, :notification_email, :updated_at)
                ON CONFLICT (tenant_id) 
                DO UPDATE SET 
                    alert_preferences = {alert_preferences_bind},
                    notification_email = :notification_email,
                    updated_at = :updated_at
            """),
            {
                "tenant_id": str(tenant_id),
                "alert_preferences": json.dumps(request.email_notifications),
                "notification_email": request.notification_email,
                "updated_at": now
            }
        )
        db.commit()
        
        return AlertPreferencesResponse(
            tenant_id=tenant_id,
            email_notifications=request.email_notifications,
            notification_email=request.notification_email,
            updated_at=now
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set alert preferences: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set alert preferences: {str(e)}"
        )


@router.get("/{tenant_id}/feature-flags", response_model=FeatureFlagsResponse)
def get_feature_flags(
    tenant_id: UUID,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Get feature flags (e.g., EDR sidecars) for a tenant."""
    try:
        _enforce_same_tenant(tenant_id, current_tenant_id)
        tenant_result = db.execute(
            text("SELECT id FROM tenants WHERE id = :tenant_id"),
            {"tenant_id": str(tenant_id)}
        ).first()
        if not tenant_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found"
            )

        _ensure_tenant_preferences_table(db)

        row = db.execute(
            text("SELECT feature_flags, updated_at FROM tenant_preferences WHERE tenant_id = :tenant_id"),
            {"tenant_id": str(tenant_id)}
        ).first()

        flags = row[0] if row and row[0] else {}
        updated_at = row[1] if row and row[1] else datetime.utcnow()
        openedr_enabled = flags.get("edr_openedr_enabled", True)
        velociraptor_enabled = flags.get("edr_velociraptor_enabled", False)

        return FeatureFlagsResponse(
            tenant_id=tenant_id,
            edr_openedr_enabled=openedr_enabled,
            edr_velociraptor_enabled=velociraptor_enabled,
            updated_at=updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get feature flags: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feature flags: {str(e)}"
        )


@router.post("/{tenant_id}/feature-flags", response_model=FeatureFlagsResponse)
def set_feature_flags(
    tenant_id: UUID,
    request: FeatureFlagsRequest,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Set feature flags (EDR sidecars) for a tenant."""
    try:
        _enforce_same_tenant(tenant_id, current_tenant_id)
        tenant_result = db.execute(
            text("SELECT id FROM tenants WHERE id = :tenant_id"),
            {"tenant_id": str(tenant_id)}
        ).first()
        if not tenant_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found"
            )

        _ensure_tenant_preferences_table(db)

        now = datetime.utcnow()
        feature_flags_bind = _json_bind("feature_flags", db)
        db.execute(
            text(f"""
                INSERT INTO tenant_preferences (tenant_id, feature_flags, updated_at)
                VALUES (:tenant_id, {feature_flags_bind}, :updated_at)
                ON CONFLICT (tenant_id)
                DO UPDATE SET
                    feature_flags = {feature_flags_bind},
                    updated_at = :updated_at
            """),
            {
                "tenant_id": str(tenant_id),
                "feature_flags": json.dumps(request.model_dump()),
                "updated_at": now,
            },
        )
        db.commit()

        return FeatureFlagsResponse(
            tenant_id=tenant_id,
            edr_openedr_enabled=request.edr_openedr_enabled,
            edr_velociraptor_enabled=request.edr_velociraptor_enabled,
            updated_at=now,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set feature flags: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set feature flags: {str(e)}"
        )


@router.post("/{tenant_id}/invitations", response_model=UserInvitationResponse)
def invite_users(
    tenant_id: UUID,
    request: UserInvitationRequest,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
    keycloak_client: KeycloakAdminClient = Depends(get_keycloak_client)
):
    """
    Invite users to a tenant.
    
    Creates user invitations and sends invitation emails.
    """
    try:
        _enforce_same_tenant(tenant_id, current_tenant_id)
        # Check if tenant exists and get realm name
        tenant_result = db.execute(
            text("SELECT id, slug FROM tenants WHERE id = :tenant_id"),
            {"tenant_id": str(tenant_id)}
        ).first()
        
        if not tenant_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found"
            )
        
        realm_name = tenant_result[1]
        invitations = []
        invitations_sent = 0
        
        # Create users in Keycloak and send invitations
        for email in request.emails:
            try:
                # Check if user already exists
                # For now, we'll create a temporary password and require password change
                temp_password = f"TempPass{tenant_id.hex[:8]}!"
                
                # Create user in Keycloak
                user_id = keycloak_client.create_user(
                    realm_name=realm_name,
                    username=email,
                    email=email,
                    password=temp_password,
                    first_name="",
                    last_name="",
                    enabled=True,
                    email_verified=False
                )
                
                # Set tenant_id attribute
                try:
                    keycloak_client.update_user_attributes(
                        realm_name=realm_name,
                        user_id=user_id,
                        attributes={
                            "tenant_id": [str(tenant_id)],
                        },
                    )
                except Exception as e:
                    logger.warning(f"Could not set tenant_id attribute: {e}")
                
                # Assign role
                try:
                    keycloak_client.assign_role(
                        realm_name=realm_name,
                        user_id=user_id,
                        role_name=request.role.upper()
                    )
                except Exception as e:
                    logger.warning(f"Could not assign role {request.role}: {e}")
                
                # Send verification email (via Keycloak Admin API)
                try:
                    keycloak_client.send_verification_email(realm_name=realm_name, user_id=user_id)
                except Exception as e:
                    logger.warning(f"Could not send verification email: {e}")
                
                invitations.append({
                    "email": email,
                    "user_id": user_id,
                    "status": "invited",
                    "role": request.role
                })
                invitations_sent += 1
                
            except Exception as e:
                logger.error(f"Failed to invite user {email}: {e}")
                invitations.append({
                    "email": email,
                    "user_id": None,
                    "status": "error",
                    "error": str(e)
                })
        
        return UserInvitationResponse(
            tenant_id=tenant_id,
            invitations_sent=invitations_sent,
            invitations=invitations,
            created_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to invite users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invite users: {str(e)}"
        )
