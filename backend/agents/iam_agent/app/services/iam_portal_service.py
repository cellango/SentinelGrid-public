"""IAM Portal Service - Business logic for IAM portal operations."""

from fastapi import HTTPException
import logging
import asyncio
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from sqlalchemy import text

from app.services.keycloak_client import KeycloakRoleClient
from app.services.birthright_service import BirthrightService
from app.models.iam_portal import (
    AppCreate, AppUpdate, App,
    EntitlementCreate, EntitlementUpdate, Entitlement,
    EntitlementMappingCreate, EntitlementMapping,
    AccessProfileCreate, AccessProfileUpdate, AccessProfile,
    UserEntitlementCreate, UserEntitlement,
    AccessRequestCreate, AccessRequestUpdate, AccessRequest,
    ApprovalCreate, ApprovalUpdate, Approval,
    UserCreate, UserUpdate, UserInfo,
    Policy, PolicyCreate, PolicyUpdate
)

logger = logging.getLogger(__name__)


class IAMPortalService:
    """Service for IAM portal operations."""
    
    def __init__(self, db: Session, tenant_id: UUID, realm_name: str):
        """Initialize IAM portal service."""
        self.db = db
        self.tenant_id = tenant_id
        self.realm_name = realm_name
        self.keycloak = KeycloakRoleClient()
        # Override realm for this tenant
        if hasattr(self.keycloak, 'realm'):
            logger.debug(f"🔍 [IAMPortalService.__init__] Setting Keycloak realm from {self.keycloak.realm} to {realm_name}")
            self.keycloak.realm = realm_name
        logger.info(f"🔍 [IAMPortalService.__init__] Initialized with tenant_id={tenant_id}, realm_name={realm_name}, keycloak.realm={self.keycloak.realm}")
    
    # ==================== Apps ====================
    
    def create_app(self, app_data: AppCreate) -> Optional[App]:
        """Create a new app."""
        try:
            # Import here to avoid circular imports
            from app.core.database import Base
            from sqlalchemy import text
            
            # Insert app
            result = self.db.execute(
                text("""
                    INSERT INTO apps (tenant_id, name, display_name, description, app_type, icon_url, is_active, config)
                    VALUES (:tenant_id, :name, :display_name, :description, :app_type, :icon_url, :is_active, :config)
                    RETURNING id, created_at, updated_at
                """),
                {
                    "tenant_id": str(self.tenant_id),
                    "name": app_data.name,
                    "display_name": app_data.display_name,
                    "description": app_data.description,
                    "app_type": app_data.app_type,
                    "icon_url": app_data.icon_url,
                    "is_active": app_data.is_active,
                    "config": app_data.config or {}
                }
            )
            row = result.fetchone()
            self.db.commit()
            
            return App(
                id=row[0],
                tenant_id=self.tenant_id,
                name=app_data.name,
                display_name=app_data.display_name,
                description=app_data.description,
                app_type=app_data.app_type,
                icon_url=app_data.icon_url,
                is_active=app_data.is_active,
                config=app_data.config,
                created_at=row[1],
                updated_at=row[2]
            )
        except Exception as e:
            logger.error(f"Failed to create app: {e}")
            self.db.rollback()
            return None
    
    def list_apps(self) -> List[App]:
        """List all apps for tenant."""
        try:
            from sqlalchemy import text
            
            result = self.db.execute(
                text("""
                    SELECT id, name, display_name, description, app_type, icon_url, is_active, config, created_at, updated_at
                    FROM apps
                    WHERE tenant_id = :tenant_id
                    ORDER BY display_name
                """),
                {"tenant_id": str(self.tenant_id)}
            )
            
            apps = []
            for row in result:
                apps.append(App(
                    id=row[0],
                    tenant_id=self.tenant_id,
                    name=row[1],
                    display_name=row[2],
                    description=row[3],
                    app_type=row[4],
                    icon_url=row[5],
                    is_active=row[6],
                    config=row[7] or {},
                    created_at=row[8],
                    updated_at=row[9]
                ))
            return apps
        except Exception as e:
            logger.error(f"Failed to list apps: {e}")
            return []
    
    # ==================== Entitlements ====================
    
    def create_entitlement(self, entitlement_data: EntitlementCreate, mappings: List[EntitlementMappingCreate]) -> Optional[Entitlement]:
        """Create a new entitlement with mappings."""
        try:
            from sqlalchemy import text
            
            # Insert entitlement
            result = self.db.execute(
                text("""
                    INSERT INTO entitlements (tenant_id, app_id, name, display_name, description, entitlement_type, is_privileged, requires_mfa, risk_level)
                    VALUES (:tenant_id, :app_id, :name, :display_name, :description, :entitlement_type, :is_privileged, :requires_mfa, :risk_level)
                    RETURNING id, created_at, updated_at
                """),
                {
                    "tenant_id": str(self.tenant_id),
                    "app_id": str(entitlement_data.app_id),
                    "name": entitlement_data.name,
                    "display_name": entitlement_data.display_name,
                    "description": entitlement_data.description,
                    "entitlement_type": entitlement_data.entitlement_type,
                    "is_privileged": entitlement_data.is_privileged,
                    "requires_mfa": entitlement_data.requires_mfa,
                    "risk_level": entitlement_data.risk_level
                }
            )
            row = result.fetchone()
            entitlement_id = row[0]
            
            # Insert mappings
            for mapping in mappings:
                self.db.execute(
                    text("""
                        INSERT INTO entitlement_mappings (entitlement_id, tenant_id, realm_name, keycloak_group_id, keycloak_group_name, keycloak_role_name, keycloak_client_id, provisioning_config)
                        VALUES (:entitlement_id, :tenant_id, :realm_name, :keycloak_group_id, :keycloak_group_name, :keycloak_role_name, :keycloak_client_id, :provisioning_config)
                    """),
                    {
                        "entitlement_id": str(entitlement_id),
                        "tenant_id": str(self.tenant_id),
                        "realm_name": mapping.realm_name,
                        "keycloak_group_id": mapping.keycloak_group_id,
                        "keycloak_group_name": mapping.keycloak_group_name,
                        "keycloak_role_name": mapping.keycloak_role_name,
                        "keycloak_client_id": mapping.keycloak_client_id,
                        "provisioning_config": mapping.provisioning_config or {}
                    }
                )
            
            self.db.commit()
            
            return Entitlement(
                id=entitlement_id,
                tenant_id=self.tenant_id,
                app_id=entitlement_data.app_id,
                name=entitlement_data.name,
                display_name=entitlement_data.display_name,
                description=entitlement_data.description,
                entitlement_type=entitlement_data.entitlement_type,
                is_privileged=entitlement_data.is_privileged,
                requires_mfa=entitlement_data.requires_mfa,
                risk_level=entitlement_data.risk_level,
                created_at=row[1],
                updated_at=row[2]
            )
        except Exception as e:
            logger.error(f"Failed to create entitlement: {e}")
            self.db.rollback()
            return None
    
    def list_entitlements(self, app_id: Optional[UUID] = None) -> List[Entitlement]:
        """List entitlements for tenant."""
        try:
            from sqlalchemy import text
            
            query = """
                SELECT id, app_id, name, display_name, description, entitlement_type, is_privileged, requires_mfa, risk_level, created_at, updated_at
                FROM entitlements
                WHERE tenant_id = :tenant_id
            """
            params = {"tenant_id": str(self.tenant_id)}
            
            if app_id:
                query += " AND app_id = :app_id"
                params["app_id"] = str(app_id)
            
            query += " ORDER BY display_name"
            
            result = self.db.execute(text(query), params)
            
            entitlements = []
            for row in result:
                entitlements.append(Entitlement(
                    id=row[0],
                    tenant_id=self.tenant_id,
                    app_id=row[1],
                    name=row[2],
                    display_name=row[3],
                    description=row[4],
                    entitlement_type=row[5],
                    is_privileged=row[6],
                    requires_mfa=row[7],
                    risk_level=row[8],
                    created_at=row[9],
                    updated_at=row[10]
                ))
            return entitlements
        except Exception as e:
            logger.error(f"Failed to list entitlements: {e}")
            return []
    
    # ==================== Access Profiles ====================
    
    def create_access_profile(self, profile_data: AccessProfileCreate) -> Optional[AccessProfile]:
        """Create a new access profile."""
        try:
            from sqlalchemy import text
            
            # Insert profile
            result = self.db.execute(
                text("""
                    INSERT INTO public.access_profiles (tenant_id, name, display_name, description, is_default, is_system, is_birthright, scope)
                    VALUES (:tenant_id, :name, :display_name, :description, :is_default, :is_system, :is_birthright, :scope)
                    RETURNING id, created_at, updated_at
                """),
                {
                    "tenant_id": str(self.tenant_id),
                    "name": profile_data.name,
                    "display_name": profile_data.display_name,
                    "description": profile_data.description,
                    "is_default": profile_data.is_default,
                    "is_system": profile_data.is_system,
                    "is_birthright": getattr(profile_data, "is_birthright", False),
                    "scope": getattr(profile_data, "scope", "all_users"),
                }
            )
            row = result.fetchone()
            profile_id = row[0]
            
            # Insert profile entitlements
            for entitlement_id in profile_data.entitlement_ids:
                self.db.execute(
                    text("""
                        INSERT INTO public.access_profile_entitlements (access_profile_id, entitlement_id)
                        VALUES (:profile_id, :entitlement_id)
                    """),
                    {
                        "profile_id": str(profile_id),
                        "entitlement_id": str(entitlement_id)
                    }
                )
            
            self.db.commit()
            
            # Fetch entitlements
            entitlements = self.list_entitlements()
            profile_entitlements = [e for e in entitlements if e.id in profile_data.entitlement_ids]
            
            return AccessProfile(
                id=profile_id,
                tenant_id=self.tenant_id,
                name=profile_data.name,
                display_name=profile_data.display_name,
                description=profile_data.description,
                is_default=profile_data.is_default,
                is_system=profile_data.is_system,
                is_birthright=getattr(profile_data, "is_birthright", False),
                scope=getattr(profile_data, "scope", "all_users"),
                entitlements=profile_entitlements,
                created_at=row[1],
                updated_at=row[2]
            )
        except Exception as e:
            logger.error(f"Failed to create access profile: {e}")
            self.db.rollback()
            return None
    
    def list_access_profiles(self) -> List[AccessProfile]:
        """List access profiles for tenant."""
        try:
            from sqlalchemy import text
            
            # Get profiles
            result = self.db.execute(
                text("""
                    SELECT id, name, display_name, description, is_default, is_system, is_birthright, scope, created_at, updated_at
                    FROM public.access_profiles
                    WHERE tenant_id = :tenant_id
                    ORDER BY is_default DESC, display_name
                """),
                {"tenant_id": str(self.tenant_id)}
            )
            
            profiles = []
            entitlements = self.list_entitlements()
            
            for row in result:
                profile_row = row
                profile_id = profile_row[0]
                
                # Get entitlements for this profile
                ent_result = self.db.execute(
                    text("""
                        SELECT entitlement_id
                        FROM public.access_profile_entitlements
                        WHERE access_profile_id = :profile_id
                    """),
                    {"profile_id": str(profile_id)}
                )
                entitlement_ids = set()
                for ent_row in ent_result:
                    val = str(ent_row[0])
                    entitlement_ids.add(val)
                profile_entitlements = [e for e in entitlements if str(e.id) in entitlement_ids]
                
                profiles.append(AccessProfile(
                    id=profile_id,
                    tenant_id=self.tenant_id,
                    name=profile_row[1],
                    display_name=profile_row[2],
                    description=profile_row[3],
                    is_default=profile_row[4],
                    is_system=profile_row[5],
                    is_birthright=profile_row[6],
                    scope=profile_row[7],
                    entitlements=profile_entitlements,
                    created_at=profile_row[8],
                    updated_at=profile_row[9]
                ))
            return profiles
        except Exception as e:
            logger.error(f"Failed to list access profiles: {e}")
            return []

    # ==================== Policies ====================

    @staticmethod
    def _policy_from_row(row) -> Policy:
        """Map raw DB row to Policy model."""
        return Policy(
            id=row[0], tenant_id=row[1], name=row[2], display_name=row[3], description=row[4],
            policy_type=row[5], scope=row[6], scope_id=row[7], policy_data=row[8],
            is_active=row[9], priority=row[10], created_at=row[11], updated_at=row[12],
            created_by=row[13], is_template=row[14], approval_required=row[15], approval_status=row[16],
        )

    def _get_admin_tenant_id(self) -> Optional[UUID]:
        return None

    def list_policies(self, policy_type: Optional[str] = None) -> List[Policy]:
        try:
            from sqlalchemy import text
            params = {"t": str(self.tenant_id)}
            filter_clause = ""
            if policy_type:
                filter_clause = "AND policy_type = :ptype"
                params["ptype"] = policy_type
            rows = self.db.execute(
                text(f"""
                    SELECT id, tenant_id, name, display_name, description, policy_type, scope, scope_id, policy_data,
                           is_active, priority, created_at, updated_at, created_by, is_template, approval_required, approval_status
                    FROM policies
                    WHERE tenant_id = :t {filter_clause}
                    ORDER BY priority ASC, created_at DESC
                """),
                params,
            ).fetchall()
            return [self._policy_from_row(r) for r in rows]
        except Exception as e:
            logger.error(f"Failed to list policies: {e}", exc_info=True)
            return []

    def list_policy_bundles(self, policy_type: Optional[str] = None) -> List[Policy]:
        raise HTTPException(status_code=503, detail="Shared policy publication and cloning require explicit admission")

    def get_policy(self, policy_id: UUID) -> Optional[Policy]:
        try:
            from sqlalchemy import text
            r = self.db.execute(
                text("""
                    SELECT id, tenant_id, name, display_name, description, policy_type, scope, scope_id, policy_data,
                           is_active, priority, created_at, updated_at, created_by, is_template, approval_required, approval_status
                    FROM policies
                    WHERE id = :id AND tenant_id = :t
                """),
                {"id": str(policy_id), "t": str(self.tenant_id)},
            ).fetchone()
            if not r:
                return None
            return Policy(
                id=r[0], tenant_id=r[1], name=r[2], display_name=r[3], description=r[4],
                policy_type=r[5], scope=r[6], scope_id=r[7], policy_data=r[8],
                is_active=r[9], priority=r[10], created_at=r[11], updated_at=r[12],
                created_by=r[13], is_template=r[14], approval_required=r[15], approval_status=r[16],
            )
        except Exception as e:
            logger.error(f"Failed to get policy: {e}", exc_info=True)
            return None

    def clone_policy_bundle(self, bundle_id: UUID, new_name: Optional[str] = None, new_display_name: Optional[str] = None, user_id: Optional[str] = None) -> Optional[Policy]:
        raise HTTPException(status_code=503, detail="Shared policy publication and cloning require explicit admission")

    def create_policy(self, payload: PolicyCreate, created_by: Optional[str] = None) -> Optional[Policy]:
        try:
            from sqlalchemy import text
            r = self.db.execute(
                text("""
                    INSERT INTO policies (tenant_id, name, display_name, description, policy_type, scope, scope_id, policy_data, is_active, priority, created_by, is_template, approval_required, approval_status)
                    VALUES (:t, :name, :display_name, :description, :ptype, :scope, :scope_id, :pdata, :is_active, :priority, :created_by, false, :approval_required, 'approved')
                    RETURNING id, created_at, updated_at
                """),
                {
                    "t": str(self.tenant_id),
                    "name": payload.name,
                    "display_name": payload.display_name,
                    "description": payload.description,
                    "ptype": payload.policy_type,
                    "scope": payload.scope or "tenant",
                    "scope_id": str(payload.scope_id) if payload.scope_id else None,
                    "pdata": payload.policy_data or {},
                    "is_active": payload.is_active if payload.is_active is not None else True,
                    "priority": payload.priority if payload.priority is not None else 100,
                    "created_by": created_by,
                    "approval_required": payload.approval_required if payload.approval_required is not None else False,
                },
            ).fetchone()
            self.db.commit()
            return self.get_policy(r[0])
        except Exception as e:
            logger.error(f"Failed to create policy: {e}", exc_info=True)
            self.db.rollback()
            return None

    def update_policy(self, policy_id: UUID, payload: PolicyUpdate) -> Optional[Policy]:
        try:
            from sqlalchemy import text
            self.db.execute(
                text("""
                    UPDATE policies
                    SET name = COALESCE(:name, name),
                        display_name = COALESCE(:display_name, display_name),
                        description = COALESCE(:description, description),
                        policy_type = COALESCE(:ptype, policy_type),
                        scope = COALESCE(:scope, scope),
                        scope_id = COALESCE(:scope_id, scope_id),
                        policy_data = COALESCE(:pdata, policy_data),
                        is_active = COALESCE(:is_active, is_active),
                        priority = COALESCE(:priority, priority),
                        approval_required = COALESCE(:approval_required, approval_required),
                        approval_status = COALESCE(:approval_status, approval_status),
                        updated_at = now()
                    WHERE id = :id AND tenant_id = :t
                """),
                {
                    "id": str(policy_id),
                    "t": str(self.tenant_id),
                    "name": payload.name,
                    "display_name": payload.display_name,
                    "description": payload.description,
                    "ptype": payload.policy_type,
                    "scope": payload.scope,
                    "scope_id": str(payload.scope_id) if payload.scope_id else None,
                    "pdata": payload.policy_data,
                    "is_active": payload.is_active,
                    "priority": payload.priority,
                    "approval_required": payload.approval_required,
                    "approval_status": payload.approval_status,
                },
            )
            self.db.commit()
            return self.get_policy(policy_id)
        except Exception as e:
            logger.error(f"Failed to update policy: {e}", exc_info=True)
            self.db.rollback()
            return None

    def list_policy_templates(self, policy_type: Optional[str] = None) -> List[Policy]:
        try:
            from sqlalchemy import text
            params = {"t": str(self.tenant_id)}
            filter_clause = "AND is_template = true"
            if policy_type:
                filter_clause += " AND policy_type = :ptype"
                params["ptype"] = policy_type
            rows = self.db.execute(
                text(f"""
                    SELECT id, tenant_id, name, display_name, description, policy_type, scope, scope_id, policy_data,
                           is_active, priority, created_at, updated_at, created_by, is_template, approval_required, approval_status
                    FROM policies
                    WHERE tenant_id = :t {filter_clause}
                    ORDER BY priority ASC, created_at DESC
                """),
                params,
            ).fetchall()
            templates: List[Policy] = []
            for r in rows:
                templates.append(Policy(
                    id=r[0], tenant_id=r[1], name=r[2], display_name=r[3], description=r[4],
                    policy_type=r[5], scope=r[6], scope_id=r[7], policy_data=r[8],
                    is_active=r[9], priority=r[10], created_at=r[11], updated_at=r[12],
                    created_by=r[13], is_template=r[14], approval_required=r[15], approval_status=r[16],
                ))
            return templates
        except Exception as e:
            logger.error(f"Failed to list policy templates: {e}", exc_info=True)
            return []

    def create_policy_from_template(self, template_id: UUID, name: str, display_name: str, created_by: Optional[str] = None) -> Optional[Policy]:
        tmpl = self.get_policy(template_id)
        if not tmpl or not tmpl.is_template:
            return None
        payload = PolicyCreate(
            name=name,
            display_name=display_name,
            description=tmpl.description,
            policy_type=tmpl.policy_type,
            scope=tmpl.scope,
            scope_id=tmpl.scope_id,
            policy_data=tmpl.policy_data,
            is_active=True,
            priority=tmpl.priority,
            approval_required=False,
        )
        return self.create_policy(payload, created_by=created_by)

    def evaluate_policy(self, policy_type: str, context: dict) -> dict:
        """Compatibility simulation delegates to the same fail-closed evaluator."""
        from app.models.policies import EvaluationContext
        from app.services.policy_service import PolicyService

        service = PolicyService(self.db, self.tenant_id, self.realm_name, load_seed_tenant=False)
        try:
            result = service.evaluate_policy(policy_type, EvaluationContext.model_validate(context))
        except Exception:
            result = service._denied("Invalid simulation context")
        return result.model_dump(mode="json")

    def list_birthrights(self) -> List[AccessProfile]:
        """List birthright access profiles (flagged)."""
        return [p for p in self.list_access_profiles() if getattr(p, "is_birthright", False)]
    
    # ==================== Users ====================
    
    def _ensure_user_profile_configured(self) -> None:
        """
        Fail-safe: Ensure User Profile is configured for the realm.
        
        If User Profile is not configured, attempts to configure it automatically.
        This ensures tenant_id attributes will persist even if realm was created
        outside of the centralized realm creation service.
        """
        try:
            import sys
            # Add /app/libs to path for sg_core imports (mounted at /app/libs in container)
            libs_path = "/app/libs"
            if libs_path not in sys.path:
                sys.path.insert(0, libs_path)
            from sg_core.keycloak_user_profile import verify_user_profile_configured, configure_realm_user_profile
            
            # Check if User Profile is configured
            is_configured = verify_user_profile_configured(self.realm_name)
            
            if not is_configured:
                logger.warning(
                    f"⚠️  User Profile not configured for realm '{self.realm_name}'. "
                    "Attempting to configure automatically (fail-safe)..."
                )
                
                # Attempt to configure User Profile
                success = configure_realm_user_profile(self.realm_name)
                
                if success:
                    logger.info(f"✅ User Profile configured for realm '{self.realm_name}' (fail-safe)")
                else:
                    logger.error(
                        f"❌ CRITICAL: Failed to configure User Profile for realm '{self.realm_name}'. "
                        "Custom attributes (tenant_id) will NOT persist!"
                    )
                    # Don't raise exception - allow user creation to continue
                    # This is a fail-safe, not a hard requirement
        except Exception as e:
            logger.warning(f"Error checking/configuring User Profile (fail-safe): {e}")
            # Don't raise exception - allow user creation to continue
    
    def create_user(self, user_data: UserCreate, actor_user_id: str) -> Optional[UserInfo]:
        """
        Create a new user in Keycloak and assign access profile.
        
        CRITICAL: Verifies User Profile is configured before creating user.
        If not configured, attempts to configure it automatically (fail-safe).
        """
        # Enforce tenant_id consistency and existence
        if str(user_data.tenant_id) != str(self.tenant_id):
            logger.error(f"Tenant mismatch: payload tenant_id={user_data.tenant_id}, context tenant_id={self.tenant_id}")
            return None
        # Verify tenant exists in DB
        try:
            from sqlalchemy import text
            result = self.db.execute(
                text("SELECT 1 FROM tenants WHERE id = :tenant_id LIMIT 1"),
                {"tenant_id": str(self.tenant_id)}
            ).first()
            if not result:
                logger.error(f"Tenant not found in database: {self.tenant_id}")
                return None
        except Exception as e:
            logger.error(f"Error verifying tenant existence: {e}")
            return None

        # Fail-safe: Verify User Profile is configured
        self._ensure_user_profile_configured()
        try:
            # If a user with this username or email already exists, delete it first so tests are idempotent
            existing_user = None
            # Try by username first
            try:
                existing_user = self.keycloak.get_user_by_username(user_data.username)
            except Exception:
                pass
            
            # If not found by username, try by email
            if not existing_user:
                try:
                    users = self.keycloak.list_users({"email": user_data.email, "exact": True})
                    if users:
                        existing_user = users[0]
                except Exception:
                    pass
            
            if existing_user and existing_user.get("id"):
                try:
                    logger.warning(f"User {user_data.username} (email: {user_data.email}) already exists in Keycloak; deleting for clean recreate")
                    self.keycloak.delete_user(existing_user["id"])
                except Exception as delete_err:
                    logger.warning(f"Failed to delete existing user {user_data.username} before recreate: {delete_err}")
            
            # Create user in Keycloak
            keycloak_user_data = {
                "username": user_data.username,
                "email": user_data.email,
                "firstName": user_data.first_name or "",
                "lastName": user_data.last_name or "",
                "enabled": True,
                "emailVerified": False,
                "attributes": {
                    "tenant_id": [str(self.tenant_id)],
                    "department": [user_data.department] if user_data.department else [],
                    "team": [user_data.team] if user_data.team else [],
                    "location": [user_data.location] if getattr(user_data, "location", None) else [],
                    "employee_type": [user_data.employee_type] if getattr(user_data, "employee_type", None) else [],
                    "is_privileged": ["true"] if user_data.is_privileged else ["false"],
                    "manager_id": [user_data.manager_id] if user_data.manager_id else []
                }
            }
            
            user_id = self.keycloak.create_user(keycloak_user_data)
            if not user_id:
                logger.error("Failed to create user in Keycloak")
                return None
            
            # Set temporary password (user will be required to change it)
            # Note: This requires additional Keycloak API call
            
            # Assign access profile if provided
            if user_data.access_profile_id:
                self._assign_access_profile_to_user(user_id, user_data.access_profile_id, actor_user_id)
            
            # Assign admin role if requested
            if user_data.make_admin:
                self.keycloak.assign_role(user_id, "TENANT_ADMIN")
                # Privileged flag usually true for admins
                if not user_data.is_privileged:
                    try:
                        user_data.is_privileged = True
                    except Exception:
                        pass
            
            # Log audit event
            self._log_audit_event("user_created", actor_user_id, target_user_id=user_id, details={
                "username": user_data.username,
                "email": user_data.email,
                "access_profile_id": str(user_data.access_profile_id) if user_data.access_profile_id else None
            })

            # Apply default birthright profile (idempotent)
            try:
                BirthrightService.apply_default_access_profile(
                    self.db,
                    tenant_id=str(self.tenant_id),
                    user_id=user_id,
                    granted_by=actor_user_id,
                )
                delta = BirthrightService.apply_attribute_rules(
                    self.db,
                    tenant_id=str(self.tenant_id),
                    user_id=user_id,
                    granted_by=actor_user_id,
                    attributes={
                        "department": user_data.department or "",
                        "team": user_data.team or "",
                        "location": getattr(user_data, "location", "") or "",
                        "manager_id": user_data.manager_id or "",
                        "employee_type": getattr(user_data, "employee_type", "") or "",
                    },
                )
                if delta.get("inserted"):
                    self._log_audit_event(
                        "birthright_rules_applied",
                        actor_user_id,
                        target_user_id=user_id,
                        details={"inserted": delta.get("inserted", 0), "revoked": delta.get("revoked", 0)},
                    )
            except Exception as br_err:
                logger.warning(f"Birthright apply failed on create for user {user_id}: {br_err}")
            
            # Fetch user info
            return self.get_user(user_id)
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return None

    async def get_user(self, user_id: str) -> Optional[UserInfo]:
        """Get user info with entitlements."""
        try:
            keycloak_user = await self.keycloak.get_user(user_id)
            if not keycloak_user:
                return None
            
            # Get user entitlements
            from sqlalchemy import text
            
            result = self.db.execute(
                text("""
                    SELECT ue.id, ue.entitlement_id, ue.granted_by, ue.granted_at, ue.expires_at, ue.status, ue.notes,
                           e.name, e.display_name, e.app_id
                    FROM user_entitlements ue
                    JOIN entitlements e ON ue.entitlement_id = e.id
                    WHERE ue.tenant_id = :tenant_id AND ue.user_id = :user_id AND ue.status = 'active'
                    ORDER BY ue.granted_at DESC
                """),
                {
                    "tenant_id": str(self.tenant_id),
                    "user_id": user_id
                }
            )

            entitlements = []
            for row in result:
                from app.models.iam_portal import Entitlement, UserEntitlement
                entitlements.append(UserEntitlement(
                    id=row[0],
                    tenant_id=self.tenant_id,
                    user_id=user_id,
                    entitlement_id=row[1],
                    entitlement=Entitlement(
                        id=row[1],
                        tenant_id=self.tenant_id,
                        app_id=row[9],
                        name=row[7],
                        display_name=row[8],
                        entitlement_type="role",
                        is_privileged=False,
                        requires_mfa=False,
                        risk_level="low",
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    ),
                    granted_by=row[2],
                    granted_at=row[3],
                    expires_at=row[4],
                    status=row[5],
                    notes=row[6],
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                ))

            # Lifecycle schedule
            lifecycle = self.db.execute(
                text(
                    """
                    SELECT activate_at, deactivate_at
                    FROM user_lifecycle_schedule
                    WHERE tenant_id = :tenant_id AND user_id = :user_id
                    LIMIT 1
                    """
                ),
                {"tenant_id": str(self.tenant_id), "user_id": user_id},
            ).fetchone()

            # Get access profile
            # TODO: Store access profile assignment in user attributes or separate table

            return UserInfo(
                user_id=user_id,
                username=keycloak_user.get("username", ""),
                email=keycloak_user.get("email", ""),
                first_name=keycloak_user.get("firstName"),
                last_name=keycloak_user.get("lastName"),
                enabled=keycloak_user.get("enabled", True),
                manager_id=keycloak_user.get("attributes", {}).get("manager_id", [None])[0] if keycloak_user.get("attributes") else None,
                department=keycloak_user.get("attributes", {}).get("department", [None])[0] if keycloak_user.get("attributes") else None,
                team=keycloak_user.get("attributes", {}).get("team", [None])[0] if keycloak_user.get("attributes") else None,
                location=keycloak_user.get("attributes", {}).get("location", [None])[0] if keycloak_user.get("attributes") else None,
                employee_type=keycloak_user.get("attributes", {}).get("employee_type", [None])[0] if keycloak_user.get("attributes") else None,
                is_privileged=str(keycloak_user.get("attributes", {}).get("is_privileged", ["false"])[0]).lower() == "true" if keycloak_user.get("attributes") else False,
                tenant_id=self.tenant_id,
                entitlements=entitlements,
                activate_at=lifecycle.activate_at if lifecycle else None,
                deactivate_at=lifecycle.deactivate_at if lifecycle else None,
            )
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return None
    
    async def list_users(self, department_filter: Optional[str] = None, team_filter: Optional[str] = None, privileged_filter: Optional[bool] = None) -> List[UserInfo]:
        """List all users for tenant with optional department/team/privileged filtering."""
        try:
            logger.info(f"🔍 [list_users] Starting - tenant_id={self.tenant_id}, realm_name={self.realm_name}, keycloak.realm={self.keycloak.realm}")
            
            # Get users from Keycloak
            keycloak_users = await self.keycloak.list_users(max=100)
            logger.info(f"🔍 [list_users] Retrieved {len(keycloak_users)} users from Keycloak realm '{self.keycloak.realm}'")
            
            # Filter by tenant_id if users have tenant attribute
            tenant_users = []
            for idx, kc_user in enumerate(keycloak_users):
                # Check if user belongs to this tenant
                attributes = kc_user.get("attributes", {})
                user_tenant_id = attributes.get("tenant_id", [None])[0] if isinstance(attributes.get("tenant_id"), list) else attributes.get("tenant_id")
                
                logger.debug(f"🔍 [list_users] User {idx+1}/{len(keycloak_users)}: id={kc_user.get('id')}, username={kc_user.get('username')}, email={kc_user.get('email')}, attributes={attributes}, user_tenant_id={user_tenant_id}")
                
                # CRITICAL: Only include users that belong to this tenant
                # No realm-based filtering - strict tenant isolation required
                should_include = user_tenant_id == str(self.tenant_id)
                
                if not should_include:
                    logger.debug(f"🔍 [list_users] Excluding user {kc_user.get('username')} - tenant_id mismatch (user_tenant_id={user_tenant_id}, expected={self.tenant_id})")
                else:
                    logger.debug(f"🔍 [list_users] Including user {kc_user.get('username')} - tenant_id matches (tenant_id={user_tenant_id})")
                
                if should_include:
                    user_info = await self.get_user(kc_user["id"])
                    if user_info:
                        # Apply additional attribute filters if provided
                        if department_filter and (user_info.department or "") != department_filter:
                            continue
                        if team_filter and (user_info.team or "") != team_filter:
                            continue
                        if privileged_filter is not None and bool(user_info.is_privileged) != privileged_filter:
                            continue
                        tenant_users.append(user_info)
                        logger.debug(f"🔍 [list_users] Added user {user_info.username} to results")
                    else:
                        logger.warning(f"🔍 [list_users] Failed to get user info for {kc_user.get('id')}")
            
            logger.info(f"🔍 [list_users] Returning {len(tenant_users)} users after filtering (from {len(keycloak_users)} total)")
            if tenant_users:
                return tenant_users

            # Fallback: if Keycloak has no tenant-scoped users (e.g., demo env without KC seed), synthesize users from DB seeds.
            fallback_users = self._list_users_from_db_fallback(
                department_filter=department_filter,
                team_filter=team_filter,
                privileged_filter=privileged_filter,
            )
            if fallback_users:
                logger.info(f"🔍 [list_users] Using DB fallback users (count={len(fallback_users)})")
            return fallback_users
        except Exception as e:
            logger.error(f"Failed to list users: {e}", exc_info=True)
            return []

    def _list_users_from_db_fallback(
        self,
        department_filter: Optional[str] = None,
        team_filter: Optional[str] = None,
        privileged_filter: Optional[bool] = None,
    ) -> List[UserInfo]:
        """
        Fallback path to return seeded personas when Keycloak has no users for the tenant.
        Uses user_tenants and user_entitlements tables with synthetic names/emails.
        """
        try:
            from sqlalchemy import text

            rows = self.db.execute(
                text("SELECT DISTINCT user_id FROM user_tenants WHERE tenant_id = :t"),
                {"t": str(self.tenant_id)},
            ).fetchall()

            users: List[UserInfo] = []
            for row in rows:
                uid = row[0]
                # Synthetic name/email for demo
                parts = uid.replace("_", " ").replace("-", " ").split()
                first = parts[0].capitalize() if parts else uid
                last = " ".join(p.capitalize() for p in parts[1:]) if len(parts) > 1 else "User"
                email = f"{uid}@{self.realm_name}.sentinelgrid.ai"

                # Pull entitlements for display
                ent_rows = self.db.execute(
                    text(
                        """
                        SELECT id, entitlement_id, granted_by, granted_at, expires_at, status, created_at, updated_at
                        FROM user_entitlements
                        WHERE tenant_id = :t AND user_id = :u
                        """
                    ),
                    {"t": str(self.tenant_id), "u": uid},
                ).fetchall()
                entitlements: List[UserEntitlement] = []
                for ent in ent_rows:
                    entitlements.append(
                        UserEntitlement(
                            id=ent[0],
                            tenant_id=self.tenant_id,
                            user_id=uid,
                            entitlement_id=ent[1],
                            entitlement=None,
                            granted_by=ent[2],
                            granted_at=ent[3],
                            expires_at=ent[4],
                            status=ent[5] or "active",
                            notes=None,
                            created_at=ent[6],
                            updated_at=ent[7],
                        )
                    )

                user_info = UserInfo(
                    user_id=uid,
                    username=uid,
                    email=email,
                    first_name=first,
                    last_name=last,
                    enabled=True,
                    manager_id=None,
                    department=None,
                    team=None,
                    location=None,
                    employee_type=None,
                    is_privileged=False,
                    access_profile_id=None,
                    tenant_id=self.tenant_id,
                    entitlements=entitlements,
                    created_at=datetime.now(timezone.utc),
                    activate_at=None,
                    deactivate_at=None,
                )

                # Apply filters
                if department_filter and (user_info.department or "") != department_filter:
                    continue
                if team_filter and (user_info.team or "") != team_filter:
                    continue
                if privileged_filter is not None and bool(user_info.is_privileged) != privileged_filter:
                    continue

                users.append(user_info)

            return users
        except Exception as e:
            logger.error(f"🔍 [list_users] DB fallback failed: {e}", exc_info=True)
            return []

    async def update_user(self, user_id: str, user_update: UserUpdate, actor_id: str) -> Optional[UserInfo]:
        """Update user attributes (privileged flag, department, team, enabled, names)."""
        try:
            kc_user = await self.keycloak.get_user(user_id)
            if not kc_user:
                logger.error(f"User {user_id} not found in Keycloak")
                return None

            # Guardrail: do not disable the last tenant admin
            if user_update.enabled is False:
                admin_ids = await self._get_tenant_admin_user_ids()
                if len(admin_ids) == 1 and user_id in admin_ids:
                    raise ValueError("Cannot disable the last tenant admin. Assign another admin first.")

            attributes = kc_user.get("attributes", {})

            def set_attr(key: str, value: Optional[str]):
                if value is None:
                    return
                attributes[key] = [value] if value != "" else []

            set_attr("department", user_update.department)
            set_attr("team", user_update.team)
            set_attr("manager_id", user_update.manager_id)
            set_attr("location", getattr(user_update, "location", None))
            set_attr("employee_type", getattr(user_update, "employee_type", None))
            if user_update.is_privileged is not None:
                attributes["is_privileged"] = ["true"] if user_update.is_privileged else ["false"]

            # Build payload
            payload = {
                "firstName": user_update.first_name if user_update.first_name is not None else kc_user.get("firstName", ""),
                "lastName": user_update.last_name if user_update.last_name is not None else kc_user.get("lastName", ""),
                "email": user_update.email if user_update.email is not None else kc_user.get("email", ""),
                "enabled": user_update.enabled if user_update.enabled is not None else kc_user.get("enabled", True),
                "attributes": attributes,
            }

            is_disabling = user_update.enabled is False and bool(kc_user.get("enabled", True))
            success = await self.keycloak.update_user(user_id, payload)
            if not success:
                logger.error(f"Failed to update user {user_id}")
                return None

            # Log audit event
            self._log_audit_event("user_updated", actor_id, target_user_id=user_id, details=user_update.model_dump())

            # Best-effort: revoke sessions immediately when disabling.
            if is_disabling:
                await self._logout_user_sessions(user_id)

            # Best-effort: re-apply default birthright profile after attribute changes (idempotent)
            try:
                if payload.get("enabled", True):
                    inserted = BirthrightService.apply_default_access_profile(
                        self.db,
                        tenant_id=str(self.tenant_id),
                        user_id=user_id,
                        granted_by=actor_id,
                    )
                    if inserted:
                        logger.info(
                            "Birthright reapplied on user update: tenant_id=%s user_id=%s inserted=%s",
                            self.tenant_id,
                            user_id,
                            inserted,
                        )
                    attr_department = (attributes.get("department") or [None])[0] if isinstance(attributes.get("department"), list) else attributes.get("department")
                    attr_team = (attributes.get("team") or [None])[0] if isinstance(attributes.get("team"), list) else attributes.get("team")
                    attr_location = (attributes.get("location") or [None])[0] if isinstance(attributes.get("location"), list) else attributes.get("location")
                    attr_employee_type = (attributes.get("employee_type") or [None])[0] if isinstance(attributes.get("employee_type"), list) else attributes.get("employee_type")
                    attr_manager = (attributes.get("manager_id") or [None])[0] if isinstance(attributes.get("manager_id"), list) else attributes.get("manager_id")
                    delta = BirthrightService.apply_attribute_rules(
                        self.db,
                        tenant_id=str(self.tenant_id),
                        user_id=user_id,
                        granted_by=actor_id,
                        attributes={
                            "department": attr_department or "",
                            "team": attr_team or "",
                            "location": attr_location or "",
                            "employee_type": attr_employee_type or "",
                            "manager_id": attr_manager or "",
                        },
                        remove_missing=True,
                    )
                    if delta.get("revoked") or delta.get("inserted"):
                        self._log_audit_event(
                            "birthright_rules_applied",
                            actor_id,
                            target_user_id=user_id,
                            details={"inserted": delta.get("inserted", 0), "revoked": delta.get("revoked", 0)},
                        )
            except Exception as br_err:
                logger.warning(f"Birthright reapply failed on update for user {user_id}: {br_err}")

            return await self.get_user(user_id)
        except ValueError:
            # Surface guardrail failures to the API layer
            raise
        except Exception as e:
            logger.error(f"Failed to update user: {e}", exc_info=True)
            return None

    async def reapply_birthrights(self, user_id: str, actor_id: str) -> Optional[UserInfo]:
        """
        Idempotently reapply default birthright profile for a user.
        Does not remove access; only adds missing entitlements from the default profile.
        """
        try:
            kc_user = await self.keycloak.get_user(user_id)
            if not kc_user:
                return None

            inserted = BirthrightService.apply_default_access_profile(
                self.db,
                tenant_id=str(self.tenant_id),
                user_id=user_id,
                granted_by=actor_id,
            )
            kc_attrs = (kc_user or {}).get("attributes") or {}
            dept = (kc_attrs.get("department") or [None])[0] if isinstance(kc_attrs.get("department"), list) else kc_attrs.get("department")
            team = (kc_attrs.get("team") or [None])[0] if isinstance(kc_attrs.get("team"), list) else kc_attrs.get("team")
            location = (kc_attrs.get("location") or [None])[0] if isinstance(kc_attrs.get("location"), list) else kc_attrs.get("location")
            employee_type = (kc_attrs.get("employee_type") or [None])[0] if isinstance(kc_attrs.get("employee_type"), list) else kc_attrs.get("employee_type")
            manager_attr = (kc_attrs.get("manager_id") or [None])[0] if isinstance(kc_attrs.get("manager_id"), list) else kc_attrs.get("manager_id")
            delta = BirthrightService.apply_attribute_rules(
                self.db,
                tenant_id=str(self.tenant_id),
                user_id=user_id,
                granted_by=actor_id,
                attributes={
                    "department": dept or "",
                    "team": team or "",
                    "location": location or "",
                    "employee_type": employee_type or "",
                    "manager_id": manager_attr or "",
                },
            )
            if delta.get("inserted") or delta.get("revoked"):
                self._log_audit_event(
                    "birthright_rules_applied",
                    actor_id,
                    target_user_id=user_id,
                    details={"inserted": delta.get("inserted", 0), "revoked": delta.get("revoked", 0)},
                )
            if inserted:
                logger.info(
                    "Birthright reapplied via API: tenant_id=%s user_id=%s inserted=%s",
                    self.tenant_id,
                    user_id,
                    inserted,
                )
            return await self.get_user(user_id)
        except Exception as e:
            logger.error(f"Failed to reapply birthrights for user {user_id}: {e}", exc_info=True)
            return None

    # ---------------- Birthright Rules ----------------
    def list_birthright_rules(self) -> List[Dict[str, Any]]:
        rows = self.db.execute(
            text(
                """
                SELECT id, tenant_id, name, attribute_key, match_value, access_profile_id, is_active, created_at, updated_at
                FROM birthright_rules
                WHERE tenant_id = :tenant_id
                ORDER BY created_at DESC
                """
            ),
            {"tenant_id": str(self.tenant_id)},
        ).fetchall()
        return [
            {
                "id": str(row.id),
                "tenant_id": str(row.tenant_id),
                "name": row.name,
                "attribute_key": row.attribute_key,
                "match_value": row.match_value,
                "access_profile_id": str(row.access_profile_id),
                "is_active": row.is_active,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]

    def create_birthright_rule(self, data: Dict[str, Any], actor_id: str) -> Optional[Dict[str, Any]]:
        attr_key = (data.get("attribute_key") or "").lower().strip()
        allowed_keys = {"department", "team", "location", "manager_id", "employee_type"}
        if attr_key not in allowed_keys:
            raise ValueError(f"attribute_key must be one of: {', '.join(sorted(allowed_keys))}")
        match_value = (data.get("match_value") or "").strip()
        if not match_value:
            raise ValueError("match_value is required")

        profile_id = str(data.get("access_profile_id"))
        # Validate profile belongs to tenant
        profile_row = self.db.execute(
            text(
                "SELECT id FROM access_profiles WHERE id = :pid AND tenant_id = :tenant LIMIT 1"
            ),
            {"pid": profile_id, "tenant": str(self.tenant_id)},
        ).fetchone()
        if not profile_row:
            raise ValueError("access_profile_id not found for this tenant")

        name = (data.get("name") or f"{attr_key}:{match_value}").strip()

        # Guardrail: prevent conflicting duplicate (same attribute_key + match_value) rules
        dup = self.db.execute(
            text(
                """
                SELECT id, access_profile_id
                FROM birthright_rules
                WHERE tenant_id = :tenant_id
                  AND attribute_key = :attr_key
                  AND match_value = :match_value
                  AND is_active = true
                LIMIT 1
                """
            ),
            {"tenant_id": str(self.tenant_id), "attr_key": attr_key, "match_value": match_value},
        ).fetchone()
        if dup:
            dup_profile = str(dup.access_profile_id)
            # If pointing to same profile, treat as idempotent and return existing
            if dup_profile == profile_id:
                return {
                    "id": str(dup.id),
                    "tenant_id": str(self.tenant_id),
                    "name": name,
                    "attribute_key": attr_key,
                    "match_value": match_value,
                    "access_profile_id": profile_id,
                    "is_active": True,
                    "created_at": None,
                    "updated_at": None,
                }
            raise ValueError("A rule for this attribute/value already exists with a different profile.")

        row = self.db.execute(
            text(
                """
                INSERT INTO birthright_rules (tenant_id, name, attribute_key, match_value, access_profile_id, is_active)
                VALUES (:tenant_id, :name, :attribute_key, :match_value, :access_profile_id, true)
                RETURNING id, tenant_id, name, attribute_key, match_value, access_profile_id, is_active, created_at, updated_at
                """
            ),
            {
                "tenant_id": str(self.tenant_id),
                "name": name,
                "attribute_key": attr_key,
                "match_value": match_value,
                "access_profile_id": profile_id,
            },
        ).fetchone()
        self.db.commit()

        self._log_audit_event(
            "birthright_rule_created",
            actor_id,
            target_user_id=None,
            details={"rule_id": str(row.id), "attribute_key": attr_key, "match_value": match_value},
        )

        return {
            "id": str(row.id),
            "tenant_id": str(row.tenant_id),
            "name": row.name,
            "attribute_key": row.attribute_key,
            "match_value": row.match_value,
            "access_profile_id": str(row.access_profile_id),
            "is_active": row.is_active,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def delete_birthright_rule(self, rule_id: str, actor_id: str) -> bool:
        deleted = self.db.execute(
            text(
                """
                DELETE FROM birthright_rules
                WHERE tenant_id = :tenant_id AND id = :rule_id
                """
            ),
            {"tenant_id": str(self.tenant_id), "rule_id": rule_id},
        )
        rowcount = int(getattr(deleted, "rowcount", 0) or 0)
        if rowcount:
            self.db.commit()
            self._log_audit_event(
                "birthright_rule_deleted",
                actor_id,
                target_user_id=None,
                details={"rule_id": rule_id},
            )
        return rowcount > 0

    def preview_birthright_rule(self, data: Dict[str, Any]) -> Dict[str, Any]:
        attr_key = (data.get("attribute_key") or "").lower().strip()
        allowed_keys = {"department", "team", "location", "manager_id", "employee_type"}
        if attr_key not in allowed_keys:
            raise ValueError(f"attribute_key must be one of: {', '.join(sorted(allowed_keys))}")
        match_value = (data.get("match_value") or "").strip().lower()
        if not match_value:
            raise ValueError("match_value is required")
        profile_id = str(data.get("access_profile_id") or "").strip()
        if not profile_id:
            raise ValueError("access_profile_id is required")

        # Get entitlements in the profile
        ent_rows = self.db.execute(
            text(
                """
                SELECT entitlement_id FROM access_profile_entitlements
                WHERE access_profile_id = :pid
                """
            ),
            {"pid": profile_id},
        ).fetchall()
        entitlements = [str(r.entitlement_id) for r in ent_rows]

        # Compute matching users (best-effort: list users and filter)
        matched_users = []
        try:
            users = asyncio.get_event_loop().run_until_complete(self.list_users())  # type: ignore
        except RuntimeError:
            # If already in an event loop, fall back to a direct fetch of entitlements only
            users = []
        for u in users:
            candidate = (
                u.department
                if attr_key == "department"
                else u.team
                if attr_key == "team"
                else u.location
                if attr_key == "location"
                else u.manager_id
                if attr_key == "manager_id"
                else getattr(u, "employee_type", None)
            )
            if (candidate or "").strip().lower() == match_value:
                matched_users.append(
                    {
                        "user_id": u.user_id,
                        "email": u.email,
                        "username": u.username,
                        "department": u.department,
                        "team": u.team,
                        "location": getattr(u, "location", None),
                        "employee_type": getattr(u, "employee_type", None),
                        "manager_id": u.manager_id,
                    }
                )

        return {
            "matches": matched_users,
            "entitlements": entitlements,
            "match_count": len(matched_users),
        }

    # ---------------- Lifecycle Schedule ----------------
    def get_lifecycle_schedule(self, user_id: str) -> Optional[Dict[str, Any]]:
        row = self.db.execute(
            text(
                """
                SELECT activate_at, deactivate_at
                FROM user_lifecycle_schedule
                WHERE tenant_id = :tenant_id AND user_id = :user_id
                LIMIT 1
                """
            ),
            {"tenant_id": str(self.tenant_id), "user_id": user_id},
        ).fetchone()
        if not row:
            return None
        return {"activate_at": row.activate_at, "deactivate_at": row.deactivate_at}

    def set_lifecycle_schedule(
        self, user_id: str, activate_at: Optional[datetime], deactivate_at: Optional[datetime], actor_id: str
    ) -> Optional[Dict[str, Any]]:
        self.db.execute(
            text(
                """
                INSERT INTO user_lifecycle_schedule (tenant_id, user_id, activate_at, deactivate_at)
                VALUES (:tenant_id, :user_id, :activate_at, :deactivate_at)
                ON CONFLICT (tenant_id, user_id)
                DO UPDATE SET activate_at = :activate_at, deactivate_at = :deactivate_at, updated_at = now()
                """
            ),
            {
                "tenant_id": str(self.tenant_id),
                "user_id": user_id,
                "activate_at": activate_at,
                "deactivate_at": deactivate_at,
            },
        )
        self.db.commit()
        self._log_audit_event(
            "lifecycle_schedule_updated",
            actor_id,
            target_user_id=user_id,
            details={"activate_at": activate_at.isoformat() if activate_at else None, "deactivate_at": deactivate_at.isoformat() if deactivate_at else None},
        )
        return {"activate_at": activate_at, "deactivate_at": deactivate_at}

    def get_user_audit(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        rows = self.db.execute(
            text(
                """
                SELECT action, actor_user_id, actor_email, details, created_at
                FROM iam_audit_log
                WHERE tenant_id = :tenant_id
                  AND target_user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"tenant_id": str(self.tenant_id), "user_id": user_id, "limit": limit},
        ).fetchall()
        return [
            {
                "action": row.action,
                "actor_user_id": row.actor_user_id,
                "actor_email": row.actor_email,
                "details": row.details,
                "created_at": row.created_at,
            }
            for row in rows
        ]

    def get_user_timeline(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Return audit events plus synthetic schedule markers (join/move/leave)."""
        events: List[Dict[str, Any]] = []

        # Base audit events
        for evt in self.get_user_audit(user_id, limit):
            events.append(evt)

        # Lifecycle schedule markers
        sched = self.db.execute(
            text(
                """
                SELECT activate_at, deactivate_at
                FROM user_lifecycle_schedule
                WHERE tenant_id = :tenant_id AND user_id = :user_id
                LIMIT 1
                """
            ),
            {"tenant_id": str(self.tenant_id), "user_id": user_id},
        ).fetchone()
        if sched and sched.activate_at:
            events.append(
                {
                    "action": "scheduled_activation",
                    "actor_user_id": None,
                    "actor_email": None,
                    "details": {},
                    "created_at": sched.activate_at,
                }
            )
        if sched and sched.deactivate_at:
            events.append(
                {
                    "action": "scheduled_offboarding",
                    "actor_user_id": None,
                    "actor_email": None,
                    "details": {},
                    "created_at": sched.deactivate_at,
                }
            )

        # Join marker (first seen audit user_created)
        events_sorted = sorted(events, key=lambda x: x.get("created_at") or datetime.min, reverse=True)
        return events_sorted[:limit]

    async def apply_lifecycle_schedules(self, actor_id: str = "system") -> Dict[str, int]:
        """
        Apply lifecycle schedules for this tenant.

        - Activate users whose activate_at is due.
        - Offboard users whose deactivate_at is due (with guardrails).
        """
        now = datetime.now(timezone.utc)
        stats = {"activated": 0, "offboarded": 0, "skipped_last_admin": 0, "errors": 0}

        # Activate any users whose start date has arrived
        due_activations = self.db.execute(
            text(
                """
                SELECT user_id, activate_at
                FROM user_lifecycle_schedule
                WHERE tenant_id = :tenant_id AND activate_at IS NOT NULL AND activate_at <= :now
                """
            ),
            {"tenant_id": str(self.tenant_id), "now": now},
        ).fetchall()

        for row in due_activations:
            user_id = row[0]
            try:
                enabled = await self._enable_user(user_id)
                if enabled:
                    stats["activated"] += 1
                    # Best-effort: reapply birthrights on activation
                    try:
                        inserted = BirthrightService.apply_default_access_profile(
                            self.db,
                            tenant_id=str(self.tenant_id),
                            user_id=user_id,
                            granted_by=actor_id,
                        )
                        kc_user = await self.keycloak.get_user(user_id)
                        attrs = (kc_user or {}).get("attributes") or {}
                        dept = (attrs.get("department") or [None])[0] if isinstance(attrs.get("department"), list) else attrs.get("department")
                        team = (attrs.get("team") or [None])[0] if isinstance(attrs.get("team"), list) else attrs.get("team")
                        location = (attrs.get("location") or [None])[0] if isinstance(attrs.get("location"), list) else attrs.get("location")
                        employee_type = (attrs.get("employee_type") or [None])[0] if isinstance(attrs.get("employee_type"), list) else attrs.get("employee_type")
                        manager_attr = (attrs.get("manager_id") or [None])[0] if isinstance(attrs.get("manager_id"), list) else attrs.get("manager_id")
                        delta = BirthrightService.apply_attribute_rules(
                            self.db,
                            tenant_id=str(self.tenant_id),
                            user_id=user_id,
                            granted_by=actor_id,
                            attributes={
                                "department": dept or "",
                                "team": team or "",
                                "location": location or "",
                                "employee_type": employee_type or "",
                                "manager_id": manager_attr or "",
                            },
                        )
                        if inserted or delta.get("inserted") or delta.get("revoked"):
                            self._log_audit_event(
                                "birthright_rules_applied",
                                actor_id,
                                target_user_id=user_id,
                                details={"inserted": (inserted or 0) + delta.get("inserted", 0), "revoked": delta.get("revoked", 0)},
                            )
                    except Exception as br_err:
                        logger.warning("Birthright reapply failed on activation for user %s: %s", user_id, br_err)

                    self._log_audit_event(
                        "user_auto_activated",
                        actor_id,
                        target_user_id=user_id,
                        details={"activate_at": row[1].isoformat() if hasattr(row[1], "isoformat") and row[1] else None},
                    )
                    # Clear activate_at so we do not reprocess
                    self.db.execute(
                        text(
                            """
                            UPDATE user_lifecycle_schedule
                            SET activate_at = NULL, updated_at = now()
                            WHERE tenant_id = :tenant_id AND user_id = :user_id
                            """
                        ),
                        {"tenant_id": str(self.tenant_id), "user_id": user_id},
                    )
                    self.db.commit()
            except Exception as e:
                logger.error("Failed to auto-activate user %s: %s", user_id, e, exc_info=True)
                self.db.rollback()
                stats["errors"] += 1

        # Offboard any users whose end date has arrived
        due_offboards = self.db.execute(
            text(
                """
                SELECT user_id, deactivate_at
                FROM user_lifecycle_schedule
                WHERE tenant_id = :tenant_id AND deactivate_at IS NOT NULL AND deactivate_at <= :now
                """
            ),
            {"tenant_id": str(self.tenant_id), "now": now},
        ).fetchall()

        for row in due_offboards:
            user_id = row[0]
            try:
                try:
                    success = await self.offboard_user(user_id, actor_id)
                except ValueError as guardrail_err:
                    logger.warning("Skipping offboard for user %s: %s", user_id, guardrail_err)
                    stats["skipped_last_admin"] += 1
                    success = False

                if success:
                    stats["offboarded"] += 1
                    self._log_audit_event(
                        "user_auto_offboarded",
                        actor_id,
                        target_user_id=user_id,
                        details={"deactivate_at": row[1].isoformat() if hasattr(row[1], "isoformat") and row[1] else None},
                    )
                    self.db.execute(
                        text(
                            """
                            UPDATE user_lifecycle_schedule
                            SET deactivate_at = NULL, updated_at = now()
                            WHERE tenant_id = :tenant_id AND user_id = :user_id
                            """
                        ),
                        {"tenant_id": str(self.tenant_id), "user_id": user_id},
                    )
                    self.db.commit()
            except Exception as e:
                logger.error("Failed to auto-offboard user %s: %s", user_id, e, exc_info=True)
                self.db.rollback()
                stats["errors"] += 1

        return stats

    async def _disable_user(self, user_id: str) -> bool:
        """Disable user in Keycloak."""
        try:
            kc_user = await self.keycloak.get_user(user_id)
            if not kc_user:
                return False
            kc_user["enabled"] = False
            return await self.keycloak.update_user(user_id, kc_user) or False
        except Exception as e:
            logger.error(f"Failed to disable user {user_id}: {e}", exc_info=True)
            return False

    async def _enable_user(self, user_id: str) -> bool:
        """Enable user in Keycloak."""
        try:
            kc_user = await self.keycloak.get_user(user_id)
            if not kc_user:
                return False
            kc_user["enabled"] = True
            return await self.keycloak.update_user(user_id, kc_user) or False
        except Exception as e:
            logger.error(f"Failed to enable user {user_id}: {e}", exc_info=True)
            return False

    async def _logout_user_sessions(self, user_id: str) -> bool:
        """Best-effort: revoke all active sessions for a user in Keycloak."""
        try:
            from app.services.keycloak_admin_client import KeycloakAdminClient

            async with KeycloakAdminClient() as kc:
                response = await kc._make_request(
                    "POST",
                    f"/realms/{self.realm_name}/users/{user_id}/logout",
                )
                if response.status_code in (200, 204):
                    return True

                logger.warning(
                    "Keycloak logout returned %s for user_id=%s realm=%s body=%s",
                    response.status_code,
                    user_id,
                    self.realm_name,
                    (response.text or "")[:300],
                )
                return False
        except Exception as e:
            logger.warning(f"Failed to revoke sessions for user {user_id}: {e}")
            return False

    async def _get_tenant_admin_user_ids(self) -> set[str]:
        """Return user_ids of TENANT_ADMIN users for this tenant within the current realm."""
        try:
            users = await self.keycloak.get_users_with_role("TENANT_ADMIN")
            admin_ids: set[str] = set()
            for user in users:
                user_id = user.get("id")
                if not user_id:
                    continue
                # Only consider enabled admins; disabled admins should not count as "remaining admin".
                if user.get("enabled") is False:
                    continue
                attrs = user.get("attributes") or {}
                tenant_attr = attrs.get("tenant_id")
                if isinstance(tenant_attr, list):
                    tenant_attr = tenant_attr[0] if tenant_attr else None
                if tenant_attr == str(self.tenant_id):
                    admin_ids.add(user_id)
            return admin_ids
        except Exception as e:
            logger.warning(f"Failed to compute tenant admin set: {e}")
            return set()

    async def offboard_user(self, user_id: str, actor_id: str) -> Dict[str, Any]:
        """
        Offboard user: disable account and revoke entitlements for this tenant.
        """
        try:
            report = {
                "user_id": user_id,
                "tenant_id": str(self.tenant_id),
                "actor_id": actor_id,
                "timestamp": datetime.utcnow().isoformat(),
                "entitlements_revoked": 0,
                "access_requests_cancelled": 0,
                "devices_marked_untrusted": 0,
                "app_roles_removed": 0,
                "sessions_revoked": False,
                "account_disabled": False,
            }

            # Guardrail: do not offboard the last tenant admin
            admin_ids = await self._get_tenant_admin_user_ids()
            if len(admin_ids) == 1 and user_id in admin_ids:
                raise ValueError("Cannot offboard the last tenant admin. Assign another admin first.")

            # Disable user
            if await self._disable_user(user_id):
                report["account_disabled"] = True
            if await self._logout_user_sessions(user_id):
                report["sessions_revoked"] = True

            # Revoke all active entitlements for this tenant/user
            result = self.db.execute(
                text("""
                    SELECT entitlement_id FROM user_entitlements
                    WHERE tenant_id = :tenant_id AND user_id = :user_id AND status = 'active'
                """),
                {"tenant_id": str(self.tenant_id), "user_id": user_id}
            )
            entitlement_ids = [row[0] for row in result]
            for ent_id in entitlement_ids:
                try:
                    self.revoke_entitlement(user_id, ent_id, actor_id)
                except Exception as revoke_err:
                    logger.warning(f"Failed to revoke entitlement {ent_id} for user {user_id}: {revoke_err}")
            report["entitlements_revoked"] = len(entitlement_ids)

            # Close open access requests for this user (best-effort)
            try:
                result = self.db.execute(
                    text("""
                        UPDATE access_requests
                        SET status = 'cancelled', resolved_at = now(), resolved_by = :actor_id, resolution_notes = 'Auto-cancel on offboarding', updated_at = now()
                        WHERE tenant_id = :tenant_id AND requested_by = :user_id AND status IN ('pending', 'approved')
                    """),
                    {"tenant_id": str(self.tenant_id), "user_id": user_id, "actor_id": actor_id},
                )
                report["access_requests_cancelled"] = result.rowcount or 0
                self.db.commit()
            except Exception as access_err:
                logger.warning("Failed to cancel access requests for user %s: %s", user_id, access_err)

            # Mark devices owned by this user as untrusted/unenrolled (best-effort; schema may vary)
            try:
                result = self.db.execute(
                    text("""
                        UPDATE assets
                        SET owner = 'offboarded', department = COALESCE(department, 'offboarded'), compliance_status = 'revoked', updated_at = now()
                        WHERE tenant_id = :tenant_id AND (owner = :owner OR (user_id IS NOT NULL AND user_id = :owner))
                    """),
                    {"tenant_id": str(self.tenant_id), "owner": user_id},
                )
                report["devices_marked_untrusted"] = result.rowcount or 0
                self.db.commit()
            except Exception as dev_err:
                logger.warning("Failed to mark devices untrusted for user %s: %s", user_id, dev_err)

            # Remove app role assignments (client roles) for this user across tenant apps
            try:
                report["app_roles_removed"] = await self._remove_app_roles_for_user(user_id)
            except Exception as app_err:
                logger.warning("Failed to remove app roles for user %s: %s", user_id, app_err)

            self._log_audit_event(
                "user_offboarded",
                actor_id,
                target_user_id=user_id,
                details=report,
            )
            return report
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to offboard user {user_id}: {e}", exc_info=True)
            return {}

    async def _remove_app_roles_for_user(self, user_id: str) -> int:
        """
        Remove all client role assignments for this user across tenant apps.

        Returns the number of roles removed.
        """
        removed = 0
        # Gather app client IDs for this tenant
        app_ids: List[str] = []
        try:
            result = self.db.execute(
                text("SELECT id FROM apps WHERE tenant_id = :tenant_id"),
                {"tenant_id": str(self.tenant_id)},
            )
            app_ids = [str(row[0]) for row in result.fetchall()]
        except Exception as e:
            logger.warning("Failed to load apps for tenant %s: %s", self.tenant_id, e)
            return removed

        for app_id in app_ids:
            try:
                roles = await self.keycloak._make_request(
                    "GET",
                    f"users/{user_id}/role-mappings/clients/{app_id}",
                )
                if not roles:
                    continue
                await self.keycloak._make_request(
                    "DELETE",
                    f"users/{user_id}/role-mappings/clients/{app_id}",
                    json_data=roles,
                )
                removed += len(roles) if isinstance(roles, list) else 0
            except Exception as e:
                logger.warning("Failed to remove client roles for user %s app %s: %s", user_id, app_id, e)
        return removed

    async def bulk_update_users(self, action: str, user_ids: List[str], actor_id: str) -> Optional[int]:
        """
        Bulk actions: suspend, offboard, mark_privileged, unmark_privileged.
        """
        valid_actions = {"suspend", "offboard", "mark_privileged", "unmark_privileged"}
        if action not in valid_actions:
            logger.error(f"Invalid bulk action: {action}")
            return None

        # Guardrail: do not suspend/offboard the last tenant admin
        if action in {"suspend", "offboard"}:
            admin_ids = await self._get_tenant_admin_user_ids()
            if len(admin_ids) == 1 and admin_ids.intersection(set(user_ids)):
                raise ValueError("Cannot suspend/offboard the last tenant admin. Assign another admin first.")

        updated = 0
        for uid in user_ids:
            try:
                if action == "suspend":
                    success = await self.update_user(uid, UserUpdate(enabled=False), actor_id)
                elif action == "offboard":
                    success = await self.offboard_user(uid, actor_id)
                elif action == "mark_privileged":
                    success = await self.update_user(uid, UserUpdate(is_privileged=True), actor_id)
                elif action == "unmark_privileged":
                    success = await self.update_user(uid, UserUpdate(is_privileged=False), actor_id)
                else:
                    success = None
                if success:
                    updated += 1
            except Exception as e:
                logger.warning(f"Bulk action '{action}' failed for user {uid}: {e}")
                continue
        return updated
    
    def _assign_access_profile_to_user(self, user_id: str, profile_id: UUID, granted_by: str):
        """Assign access profile to user (grants all entitlements in profile)."""
        try:
            from sqlalchemy import text
            
            # Get entitlements in profile
            result = self.db.execute(
                text("""
                    SELECT entitlement_id
                    FROM access_profile_entitlements
                    WHERE access_profile_id = :profile_id
                """),
                {"profile_id": str(profile_id)}
            )
            entitlement_ids = [UUID(row[0]) for row in result]
            
            # Grant each entitlement
            for entitlement_id in entitlement_ids:
                self.grant_entitlement(user_id, entitlement_id, granted_by)
        except Exception as e:
            logger.error(f"Failed to assign access profile: {e}")
    
    # ==================== Entitlements ====================
    
    def grant_entitlement(self, user_id: str, entitlement_id: UUID, granted_by: str, expires_at: Optional[datetime] = None) -> bool:
        """Grant entitlement to user (updates Keycloak and database)."""
        try:
            from sqlalchemy import text
            
            # Get entitlement mappings
            result = self.db.execute(
                text("""
                    SELECT keycloak_group_id, keycloak_group_name, keycloak_role_name, keycloak_client_id
                    FROM entitlement_mappings
                    WHERE entitlement_id = :entitlement_id AND tenant_id = :tenant_id
                """),
                {
                    "entitlement_id": str(entitlement_id),
                    "tenant_id": str(self.tenant_id)
                }
            )
            
            mappings = result.fetchall()
            if not mappings:
                logger.warning(f"No mappings found for entitlement {entitlement_id}")
                return False
            
            # Apply Keycloak changes
            for mapping in mappings:
                group_id, group_name, role_name, client_id = mapping
                
                # Add to Keycloak group if specified
                if group_id or group_name:
                    # TODO: Implement group assignment via Keycloak Admin API
                    pass
                
                # Assign Keycloak role if specified
                if role_name:
                    self.keycloak.assign_role(user_id, role_name)
            
            # Record in database
            self.db.execute(
                text("""
                    INSERT INTO user_entitlements (tenant_id, user_id, entitlement_id, granted_by, expires_at, status)
                    VALUES (:tenant_id, :user_id, :entitlement_id, :granted_by, :expires_at, 'active')
                    ON CONFLICT DO NOTHING
                """),
                {
                    "tenant_id": str(self.tenant_id),
                    "user_id": user_id,
                    "entitlement_id": str(entitlement_id),
                    "granted_by": granted_by,
                    "expires_at": expires_at
                }
            )
            
            self.db.commit()
            
            # Log audit event
            self._log_audit_event("entitlement_granted", granted_by, target_user_id=user_id, target_entitlement_id=entitlement_id)
            
            return True
        except Exception as e:
            logger.error(f"Failed to grant entitlement: {e}")
            self.db.rollback()
            return False
    
    def revoke_entitlement(self, user_id: str, entitlement_id: UUID, revoked_by: str) -> bool:
        """Revoke entitlement from user."""
        try:
            from sqlalchemy import text
            
            # Get entitlement mappings
            result = self.db.execute(
                text("""
                    SELECT keycloak_group_id, keycloak_group_name, keycloak_role_name, keycloak_client_id
                    FROM entitlement_mappings
                    WHERE entitlement_id = :entitlement_id AND tenant_id = :tenant_id
                """),
                {
                    "entitlement_id": str(entitlement_id),
                    "tenant_id": str(self.tenant_id)
                }
            )
            
            mappings = result.fetchall()
            
            # Remove from Keycloak
            for mapping in mappings:
                group_id, group_name, role_name, client_id = mapping
                
                if role_name:
                    self.keycloak.remove_role(user_id, role_name)
            
            # Update database
            self.db.execute(
                text("""
                    UPDATE user_entitlements
                    SET status = 'revoked', updated_at = now()
                    WHERE tenant_id = :tenant_id AND user_id = :user_id AND entitlement_id = :entitlement_id AND status = 'active'
                """),
                {
                    "tenant_id": str(self.tenant_id),
                    "user_id": user_id,
                    "entitlement_id": str(entitlement_id)
                }
            )
            
            self.db.commit()
            
            # Log audit event
            self._log_audit_event("entitlement_revoked", revoked_by, target_user_id=user_id, target_entitlement_id=entitlement_id)
            
            return True
        except Exception as e:
            logger.error(f"Failed to revoke entitlement: {e}")
            self.db.rollback()
            return False
    
    # ==================== Access Requests ====================
    
    def create_access_request(self, request_data: AccessRequestCreate, requested_by: str) -> Optional[AccessRequest]:
        """Create an access request."""
        try:
            from sqlalchemy import text
            
            # Check if entitlement requires approval
            result = self.db.execute(
                text("""
                    SELECT is_privileged, risk_level
                    FROM entitlements
                    WHERE id = :entitlement_id AND tenant_id = :tenant_id
                """),
                {
                    "entitlement_id": str(request_data.entitlement_id),
                    "tenant_id": str(self.tenant_id)
                }
            )
            row = result.fetchone()
            if not row:
                logger.error(f"Entitlement {request_data.entitlement_id} not found")
                return None
            
            is_privileged, risk_level = row
            
            # Create request
            result = self.db.execute(
                text("""
                    INSERT INTO access_requests (tenant_id, requested_by, entitlement_id, reason, duration_days, status)
                    VALUES (:tenant_id, :requested_by, :entitlement_id, :reason, :duration_days, 'pending')
                    RETURNING id, requested_at, created_at, updated_at
                """),
                {
                    "tenant_id": str(self.tenant_id),
                    "requested_by": requested_by,
                    "entitlement_id": str(request_data.entitlement_id),
                    "reason": request_data.reason,
                    "duration_days": request_data.duration_days
                }
            )
            row = result.fetchone()
            request_id = row[0]
            
            # Create approvals if privileged
            if is_privileged:
                # TODO: Determine approvers (manager, app owner, admin)
                # For now, create a single admin approval
                self.db.execute(
                    text("""
                        INSERT INTO approvals (access_request_id, approver_id, approver_type, status)
                        VALUES (:request_id, :approver_id, 'admin', 'pending')
                    """),
                    {
                        "request_id": str(request_id),
                        "approver_id": requested_by  # TODO: Get actual approver
                    }
                )
            
            self.db.commit()
            
            # Log audit event
            self._log_audit_event("access_requested", requested_by, target_access_request_id=request_id, target_entitlement_id=request_data.entitlement_id)
            
            return AccessRequest(
                id=request_id,
                tenant_id=self.tenant_id,
                requested_by=requested_by,
                entitlement_id=request_data.entitlement_id,
                reason=request_data.reason,
                duration_days=request_data.duration_days,
                status="pending",
                requested_at=row[1],
                created_at=row[2],
                updated_at=row[3]
            )
        except Exception as e:
            logger.error(f"Failed to create access request: {e}")
            self.db.rollback()
            return None
    
    def approve_access_request(self, request_id: UUID, approver_id: str, notes: Optional[str] = None) -> bool:
        """Approve an access request."""
        try:
            from sqlalchemy import text
            
            # Get request
            result = self.db.execute(
                text("""
                    SELECT requested_by, entitlement_id, duration_days
                    FROM access_requests
                    WHERE id = :request_id AND tenant_id = :tenant_id AND status = 'pending'
                """),
                {
                    "request_id": str(request_id),
                    "tenant_id": str(self.tenant_id)
                }
            )
            row = result.fetchone()
            if not row:
                return False
            
            requested_by, entitlement_id, duration_days = row
            
            # Calculate expiration if temporary
            expires_at = None
            if duration_days:
                expires_at = datetime.now() + timedelta(days=duration_days)
            
            # Grant entitlement
            if not self.grant_entitlement(requested_by, UUID(entitlement_id), approver_id, expires_at):
                return False
            
            # Update request
            self.db.execute(
                text("""
                    UPDATE access_requests
                    SET status = 'approved', resolved_at = now(), resolved_by = :resolved_by, resolution_notes = :notes, updated_at = now()
                    WHERE id = :request_id
                """),
                {
                    "request_id": str(request_id),
                    "resolved_by": approver_id,
                    "notes": notes
                }
            )
            
            # Update approvals
            self.db.execute(
                text("""
                    UPDATE approvals
                    SET status = 'approved', approved_at = now(), notes = :notes, updated_at = now()
                    WHERE access_request_id = :request_id AND approver_id = :approver_id
                """),
                {
                    "request_id": str(request_id),
                    "approver_id": approver_id,
                    "notes": notes
                }
            )
            
            self.db.commit()
            
            # Log audit event
            self._log_audit_event("access_approved", approver_id, target_access_request_id=request_id, target_entitlement_id=UUID(entitlement_id))
            
            return True
        except Exception as e:
            logger.error(f"Failed to approve access request: {e}")
            self.db.rollback()
            return False
    
    def deny_access_request(self, request_id: UUID, approver_id: str, notes: Optional[str] = None) -> bool:
        """Deny an access request."""
        try:
            from sqlalchemy import text
            
            # Update request
            self.db.execute(
                text("""
                    UPDATE access_requests
                    SET status = 'denied', resolved_at = now(), resolved_by = :resolved_by, resolution_notes = :notes, updated_at = now()
                    WHERE id = :request_id AND tenant_id = :tenant_id AND status = 'pending'
                """),
                {
                    "request_id": str(request_id),
                    "tenant_id": str(self.tenant_id),
                    "resolved_by": approver_id,
                    "notes": notes
                }
            )
            
            # Update approvals
            self.db.execute(
                text("""
                    UPDATE approvals
                    SET status = 'denied', notes = :notes, updated_at = now()
                    WHERE access_request_id = :request_id AND approver_id = :approver_id
                """),
                {
                    "request_id": str(request_id),
                    "approver_id": approver_id,
                    "notes": notes
                }
            )
            
            self.db.commit()
            
            # Log audit event
            self._log_audit_event("access_denied", approver_id, target_access_request_id=request_id)
            
            return True
        except Exception as e:
            logger.error(f"Failed to deny access request: {e}")
            self.db.rollback()
            return False
    
    def list_access_requests(self, user_id: Optional[str] = None, status: Optional[str] = None) -> List[AccessRequest]:
        """List access requests."""
        try:
            from sqlalchemy import text
            
            query = """
                SELECT id, requested_by, entitlement_id, reason, duration_days, status, requested_at, resolved_at, resolved_by, resolution_notes, created_at, updated_at
                FROM access_requests
                WHERE tenant_id = :tenant_id
            """
            params = {"tenant_id": str(self.tenant_id)}
            
            if user_id:
                query += " AND requested_by = :user_id"
                params["user_id"] = user_id
            
            if status:
                query += " AND status = :status"
                params["status"] = status
            
            query += " ORDER BY requested_at DESC"
            
            result = self.db.execute(text(query), params)
            
            requests = []
            for row in result:
                requests.append(AccessRequest(
                    id=row[0],
                    tenant_id=self.tenant_id,
                    requested_by=row[1],
                    entitlement_id=UUID(row[2]),
                    reason=row[3],
                    duration_days=row[4],
                    status=row[5],
                    requested_at=row[6],
                    resolved_at=row[7],
                    resolved_by=row[8],
                    resolution_notes=row[9],
                    created_at=row[10],
                    updated_at=row[11]
                ))
            return requests
        except Exception as e:
            logger.error(f"Failed to list access requests: {e}")
            return []
    
    # ==================== Audit Logging ====================
    
    def _log_audit_event(self, action: str, actor_user_id: str, target_user_id: Optional[str] = None,
                        target_entitlement_id: Optional[UUID] = None, target_access_request_id: Optional[UUID] = None,
                        details: Optional[Dict[str, Any]] = None):
        """Log IAM audit event."""
        try:
            from sqlalchemy import text
            
            # Get actor email from Keycloak
            actor_email = None
            actor_user = self.keycloak.get_user(actor_user_id)
            if actor_user:
                actor_email = actor_user.get("email")
            
            import json
            # Use CAST for JSONB to avoid SQL syntax issues with parameterized queries
            self.db.execute(
                text("""
                    INSERT INTO iam_audit_log (tenant_id, realm_name, action, actor_user_id, actor_email, target_user_id, target_entitlement_id, target_access_request_id, details)
                    VALUES (:tenant_id, :realm_name, :action, :actor_user_id, :actor_email, :target_user_id, :target_entitlement_id, :target_access_request_id, CAST(:details AS jsonb))
                """),
                {
                    "tenant_id": str(self.tenant_id),
                    "realm_name": self.realm_name,
                    "action": action,
                    "actor_user_id": actor_user_id,
                    "actor_email": actor_email,
                    "target_user_id": target_user_id,
                    "target_entitlement_id": str(target_entitlement_id) if target_entitlement_id else None,
                    "target_access_request_id": str(target_access_request_id) if target_access_request_id else None,
                    "details": json.dumps(details or {})
                }
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
