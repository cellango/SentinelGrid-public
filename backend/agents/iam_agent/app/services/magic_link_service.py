"""
Magic Link Service for passwordless authentication.

Generates secure tokens and sends magic links via email.
"""

import logging
import secrets
import hashlib
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.services.passwordless_store import PasswordlessStore
from app.services.audit_service import AuditService
from app.core.config import settings

logger = logging.getLogger(__name__)


class MagicLinkService:
    """Service for managing magic links."""
    
    def __init__(self):
        self.keycloak_admin = KeycloakAdminClient()
        self.store = PasswordlessStore(prefix="passwordless:magic")
        self.ttl_seconds = 900  # 15 minutes

    @staticmethod
    def _resolve_realm_and_client(email: str) -> Tuple[str, str]:
        """Map email to realm/client_id (demo vs default)."""
        realm = settings.KEYCLOAK_REALM
        client_id = "sentinelgrid-web"
        email_lower = email.lower()
        if email_lower.endswith("@demo.sentinelgrid.ai"):
            realm = "demo"
            client_id = "demo-web"
        return realm, client_id

    @staticmethod
    def _extract_tenant_id(user: dict) -> Optional[str]:
        """Pull tenant_id from Keycloak user attributes if present."""
        attributes = user.get("attributes") or {}
        tenant_attr = attributes.get("tenant_id")
        if isinstance(tenant_attr, list) and tenant_attr:
            return tenant_attr[0]
        if isinstance(tenant_attr, str):
            return tenant_attr
        return None
    
    async def generate_magic_link(
        self,
        email: str,
        redirect_uri: Optional[str] = None
    ) -> Dict:
        """
        Generate a magic link token.
        
        Creates a secure token, stores it temporarily, and returns token info.
        In production, would send email with magic link URL.
        """
        realm, client_id = self._resolve_realm_and_client(email)
        
        # Check if user exists
        try:
            async with self.keycloak_admin as kc:
                response = await kc._make_request(
                    "GET",
                    f"/realms/{realm}/users",
                    params={"email": email, "exact": "true"}
                )
                response.raise_for_status()
                users = response.json()
                
                if not users:
                    raise ValueError("User not found")
                
                user = users[0]
                user_id = user.get("id")
                tenant_id = self._extract_tenant_id(user)
        except Exception as e:
            logger.warning(f"User lookup failed for {email}: {e}")
            # Still generate token to prevent email enumeration
            user_id = None
            tenant_id = None
        
        # Generate secure token
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Store token (Redis if available, fallback to memory) with TTL
        expires_at = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)
        self.store.save(
            token_hash,
            {
                "email": email,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "realm": realm,
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.utcnow().isoformat(),
                "type": "magic_link",
            },
            ttl_seconds=self.ttl_seconds,
        )
        
        # In production, send email with magic link
        # magic_link_url = f"{settings.FRONTEND_URL}/auth/magic-link?token={token}"
        # await send_email(email, "Sign in to SentinelGrid", magic_link_url)
        
        logger.info(f"Magic link generated for {email}")

        AuditService.log_auth_event(
            realm_name=realm,
            action="passwordless_magic_link_sent",
            actor_email=email,
            actor_user_id=user_id,
            details={"redirect_uri": redirect_uri},
        )
        
        return {
            "token": token,
            "expires_in_seconds": self.ttl_seconds,
            "expires_at": expires_at.isoformat()
        }
    
    async def verify_magic_link(self, token: str, client_info: Optional[dict] = None) -> Dict:
        """
        Verify a magic link token.
        
        Checks if token is valid and not expired.
        Returns user info if valid.
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Check token store (single-use)
        token_data = self.store.consume(token_hash)
        if not token_data:
            return {"valid": False, "error": "Invalid or expired token"}

        user_id = token_data.get("user_id")
        realm = token_data.get("realm") or settings.KEYCLOAK_REALM
        client_id = token_data.get("client_id") or "sentinelgrid-web"

        if not user_id:
            logger.warning("Magic link verified but user_id missing (likely non-existent user)")
            return {"valid": False, "error": "Invalid token"}

        # Issue real Keycloak tokens via token exchange
        tokens: Optional[Dict[str, str]] = None
        try:
            async with self.keycloak_admin as kc:
                tokens = await kc.exchange_token_for_user(
                    realm=realm,
                    user_id=user_id,
                    client_id=client_id,
                    scope="openid offline_access",
                )
        except Exception as exc:
            logger.error(f"Token exchange failed during magic link verify: {exc}", exc_info=True)

        if not tokens or "access_token" not in tokens:
            return {"valid": False, "error": "Failed to issue tokens"}

        AuditService.log_auth_event(
            realm_name=realm,
            action="passwordless_magic_link_verify",
            actor_user_id=user_id,
            actor_email=token_data.get("email"),
            details={"success": True},
            ip_address=(client_info or {}).get("ip_address") if client_info else None,
            user_agent=(client_info or {}).get("user_agent") if client_info else None,
        )

        return {
            "valid": True,
            "email": token_data.get("email"),
            "user_id": user_id,
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "expires_in": tokens.get("expires_in", 3600)
        }
