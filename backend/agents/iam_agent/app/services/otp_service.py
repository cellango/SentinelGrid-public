"""
OTP Service for passwordless authentication.

Generates and verifies one-time password codes.
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


class OTPService:
    """Service for managing OTP codes."""
    
    def __init__(self):
        self.keycloak_admin = KeycloakAdminClient()
        self.store = PasswordlessStore(prefix="passwordless:otp")
        self.ttl_seconds = 300  # 5 minutes

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
    
    async def generate_otp(self, email: str) -> Dict:
        """
        Generate a 6-digit OTP code.
        
        Creates a secure code, stores it temporarily, and sends via email/SMS.
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
            # Still generate OTP to prevent email enumeration
            user_id = None
            tenant_id = None
        
        # Generate 6-digit OTP
        otp_code = f"{secrets.randbelow(1000000):06d}"
        otp_code_hash = hashlib.sha256(otp_code.encode()).hexdigest()
        request_token = secrets.token_urlsafe(16)  # Token to identify this OTP request
        token_hash = hashlib.sha256(request_token.encode()).hexdigest()
        
        # Store OTP (Redis if available, fallback to memory) with TTL and hashed code
        expires_at = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)
        self.store.save(
            token_hash,
            {
                "email": email,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "realm": realm,
                "client_id": client_id,
                "otp_code_hash": otp_code_hash,
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.utcnow().isoformat(),
                "attempts": 0,
                "type": "otp",
            },
            ttl_seconds=self.ttl_seconds,
        )
        
        # In production, send OTP via email/SMS
        # await send_email(email, "Your SentinelGrid sign-in code", f"Your code is: {otp_code}")
        # or
        # await send_sms(phone, f"Your SentinelGrid code is: {otp_code}")
        
        logger.info(f"OTP generated for {email}")

        AuditService.log_auth_event(
            realm_name=realm,
            action="passwordless_otp_sent",
            actor_email=email,
            actor_user_id=user_id,
            details={"delivery": "email_or_sms_stub"},
        )
        
        return {
            "token": request_token,  # Return token, not the actual OTP code
            "expires_in_seconds": self.ttl_seconds,  # 5 minutes
            "expires_at": expires_at.isoformat()
        }
    
    async def verify_otp(self, code: str, token: str, client_info: Optional[dict] = None) -> Dict:
        """
        Verify an OTP code.
        
        Checks if code is valid, not expired, and hasn't exceeded max attempts.
        """
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        otp_data = self.store.get(token_hash)
        if not otp_data:
            return {"valid": False, "error": "Invalid OTP request"}

        # Check expiration
        expires_at = datetime.fromisoformat(otp_data["expires_at"])
        ttl_remaining = int(max((expires_at - datetime.utcnow()).total_seconds(), 0))
        if datetime.utcnow() > expires_at:
            self.store.delete(token_hash)
            return {"valid": False, "error": "OTP expired"}

        # Check attempts (max 3 attempts)
        attempts = otp_data.get("attempts", 0)
        if attempts >= 3:
            self.store.delete(token_hash)
            return {"valid": False, "error": "Max attempts exceeded"}

        if code_hash != otp_data.get("otp_code_hash"):
            otp_data["attempts"] = attempts + 1
            # Persist updated attempts with remaining TTL
            self.store.save(token_hash, otp_data, ttl_seconds=max(ttl_remaining, 1))
            return {"valid": False, "error": "Invalid code"}

        # OTP is valid; consume entry for single-use
        self.store.delete(token_hash)
        user_id = otp_data.get("user_id")
        realm = otp_data.get("realm") or settings.KEYCLOAK_REALM
        client_id = otp_data.get("client_id") or "sentinelgrid-web"

        if not user_id:
            logger.warning("OTP verified but user_id missing (likely non-existent user)")
            return {"valid": False, "error": "Invalid token"}

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
            logger.error(f"Token exchange failed during OTP verify: {exc}", exc_info=True)

        if not tokens or "access_token" not in tokens:
            return {"valid": False, "error": "Failed to issue tokens"}

        AuditService.log_auth_event(
            realm_name=realm,
            action="passwordless_otp_verify",
            actor_user_id=user_id,
            actor_email=otp_data.get("email"),
            details={"success": True},
            ip_address=(client_info or {}).get("ip_address") if client_info else None,
            user_agent=(client_info or {}).get("user_agent") if client_info else None,
        )

        return {
            "valid": True,
            "email": otp_data.get("email"),
            "user_id": user_id,
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "expires_in": tokens.get("expires_in", 3600)
        }
