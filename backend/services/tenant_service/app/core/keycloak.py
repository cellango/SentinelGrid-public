"""Keycloak Admin API client for tenant provisioning."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError

from app.core.config import settings

logger = logging.getLogger(__name__)


class KeycloakAdminClient:
    """Client for Keycloak Admin API operations."""

    def __init__(self):
        """Initialize Keycloak admin client."""
        try:
            self.admin = self._realm_admin("master")
            logger.info("Connected to Keycloak admin at %s", settings.KEYCLOAK_URL)
        except Exception as exc:
            logger.error("Failed to initialize Keycloak admin client: %s", exc)
            raise

    def _realm_admin(self, realm_name: str) -> KeycloakAdmin:
        """Build a Keycloak admin client using configured runtime auth."""
        kwargs: Dict[str, Any] = {
            "server_url": settings.KEYCLOAK_URL,
            "realm_name": realm_name,
            "verify": settings.KEYCLOAK_VERIFY_TLS,
        }
        if settings.KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT and settings.KEYCLOAK_ADMIN_CLIENT_SECRET:
            kwargs.update(
                {
                    "client_id": settings.KEYCLOAK_ADMIN_CLIENT_ID,
                    "client_secret_key": settings.KEYCLOAK_ADMIN_CLIENT_SECRET,
                    "user_realm_name": settings.KEYCLOAK_ADMIN_TOKEN_REALM,
                }
            )
        else:
            kwargs.update(
                {
                    "username": settings.KEYCLOAK_ADMIN_USER,
                    "password": settings.KEYCLOAK_ADMIN_PASSWORD,
                }
            )
            if realm_name != settings.KEYCLOAK_ADMIN_TOKEN_REALM:
                kwargs["user_realm_name"] = settings.KEYCLOAK_ADMIN_TOKEN_REALM
        return KeycloakAdmin(**kwargs)

    def create_realm(
        self,
        realm_name: str,
        enabled: bool = True,
        display_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new Keycloak realm."""
        try:
            try:
                existing = self.admin.get_realm(realm_name)
                logger.warning("Realm %s already exists", realm_name)
                return existing
            except KeycloakError as exc:
                if exc.response_code != 404:
                    raise

            realm_data = {
                "realm": realm_name,
                "enabled": enabled,
                "displayName": display_name or realm_name,
                "registrationAllowed": False,
                "registrationEmailAsUsername": False,
                "rememberMe": True,
                "verifyEmail": False,
                "loginWithEmailAllowed": True,
                "duplicateEmailsAllowed": False,
                "resetPasswordAllowed": True,
                "editUsernameAllowed": False,
                "bruteForceProtected": True,
            }

            self.admin.create_realm(realm_data, skip_exists=False)
            logger.info("Created realm: %s", realm_name)
            return self.admin.get_realm(realm_name)
        except KeycloakError as exc:
            logger.error("Failed to create realm %s: %s", realm_name, exc)
            raise

    def create_client(
        self,
        realm_name: str,
        client_id: str,
        client_type: str = "public",
        redirect_uris: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Create a client in a realm."""
        try:
            realm_admin = self._realm_admin(realm_name)
            clients = realm_admin.get_clients()
            for client in clients:
                if client.get("clientId") == client_id:
                    logger.warning("Client %s already exists in realm %s", client_id, realm_name)
                    return client

            client_data = {
                "clientId": client_id,
                "enabled": True,
                "publicClient": client_type == "public",
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": True,
                "serviceAccountsEnabled": client_type == "confidential",
                "redirectUris": redirect_uris or ["*"],
                "webOrigins": ["*"],
            }

            client_uuid = realm_admin.create_client(client_data)
            client = realm_admin.get_client(client_uuid)
            logger.info("Created client %s in realm %s", client_id, realm_name)
            return client
        except KeycloakError as exc:
            logger.error("Failed to create client %s: %s", client_id, exc)
            raise

    def create_user(
        self,
        realm_name: str,
        username: str,
        email: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        enabled: bool = True,
        email_verified: bool = True,
    ) -> str:
        """Create a user in a realm."""
        try:
            realm_admin = self._realm_admin(realm_name)
            user_data = {
                "username": username,
                "email": email,
                "firstName": first_name or "",
                "lastName": last_name or "",
                "enabled": enabled,
                "emailVerified": email_verified,
            }
            user_uuid = realm_admin.create_user(user_data)
            realm_admin.set_user_password(user_uuid, password, temporary=False)
            logger.info("Created user %s in realm %s", username, realm_name)
            return user_uuid
        except KeycloakError as exc:
            logger.error("Failed to create user %s: %s", username, exc)
            raise

    def assign_role(self, realm_name: str, user_id: str, role_name: str) -> None:
        """Assign a realm role to a user."""
        try:
            realm_admin = self._realm_admin(realm_name)
            try:
                role = realm_admin.get_realm_role(role_name)
            except KeycloakError as exc:
                if exc.response_code != 404:
                    raise
                logger.info("Creating role %s in realm %s", role_name, realm_name)
                realm_admin.create_realm_role({"name": role_name}, skip_exists=False)
                role = realm_admin.get_realm_role(role_name)

            realm_admin.assign_realm_roles(user_id, [role])
            logger.info("Assigned role %s to user %s", role_name, user_id)
        except KeycloakError as exc:
            logger.error("Failed to assign role %s: %s", role_name, exc)
            raise

    def add_tenant_id_mapper(self, realm_name: str, client_id: str) -> None:
        """Add tenant_id protocol mapper to a client."""
        try:
            realm_admin = self._realm_admin(realm_name)
            clients = realm_admin.get_clients()
            client_uuid = next(
                (client["id"] for client in clients if client.get("clientId") == client_id),
                None,
            )
            if not client_uuid:
                raise ValueError(f"Client {client_id} not found")

            mappers = realm_admin.get_client_protocol_mappers(client_uuid)
            for mapper in mappers:
                if mapper.get("name") == "tenant-id-mapper":
                    logger.warning("Tenant ID mapper already exists for client %s", client_id)
                    return

            mapper_data = {
                "name": "tenant-id-mapper",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-attribute-mapper",
                "config": {
                    "user.attribute": "tenant_id",
                    "claim.name": "tenant_id",
                    "jsonType.label": "String",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "true",
                },
            }

            realm_admin.create_client_protocol_mapper(mapper_data, client_uuid)
            logger.info("Added tenant_id mapper to client %s", client_id)
        except KeycloakError as exc:
            logger.error("Failed to add tenant_id mapper: %s", exc)
            raise

    def update_user_attributes(
        self,
        realm_name: str,
        user_id: str,
        attributes: Dict[str, Any],
    ) -> None:
        """Merge custom attributes onto a Keycloak user."""
        try:
            realm_admin = self._realm_admin(realm_name)
            user = realm_admin.get_user(user_id)
            current_attributes = user.get("attributes", {})
            current_attributes.update(attributes)
            realm_admin.update_user(user_id, {"attributes": current_attributes})
            logger.info("Updated attributes for user %s in realm %s", user_id, realm_name)
        except KeycloakError as exc:
            logger.error("Failed to update attributes for user %s: %s", user_id, exc)
            raise

    def send_verification_email(self, realm_name: str, user_id: str) -> None:
        """Send verification email to a user."""
        try:
            realm_admin = self._realm_admin(realm_name)
            realm_admin.send_verify_email(user_id)
            logger.info("Sent verification email to user %s", user_id)
        except KeycloakError as exc:
            logger.error("Failed to send verification email: %s", exc)
            raise
