"""
Backup code management for MFA recovery.

Stores hashed backup codes in Keycloak user attributes to avoid plaintext exposure.
Each code is single-use; verification consumes the matching hash.
"""

import hashlib
import logging
import secrets
from typing import Dict, List, Optional, Tuple

from app.services.keycloak_admin_client import KeycloakAdminClient
from app.services.audit_service import AuditService
from app.core.config import settings

logger = logging.getLogger(__name__)


class BackupCodeService:
    """Manage creation and verification of backup (recovery) codes."""

    ATTRIBUTE_KEY = "backup_codes"

    def __init__(self, keycloak_client: Optional[KeycloakAdminClient] = None):
        self.keycloak_admin = keycloak_client or KeycloakAdminClient()
        self.num_codes = 8

    @staticmethod
    def _hash_code(code: str) -> str:
        """Hash a backup code for storage."""
        return hashlib.sha256(code.encode()).hexdigest()

    async def _get_user(self, kc: KeycloakAdminClient, realm: str, user_id: str) -> Dict:
        """Fetch user representation."""
        resp = await kc._make_request("GET", f"/realms/{realm}/users/{user_id}")
        resp.raise_for_status()
        return resp.json()

    async def _save_attributes(
        self,
        kc: KeycloakAdminClient,
        realm: str,
        user_id: str,
        attributes: Dict[str, List[str]]
    ) -> None:
        """Persist updated attributes."""
        resp = await kc._make_request(
            "PUT",
            f"/realms/{realm}/users/{user_id}",
            json_data={"attributes": attributes},
        )
        resp.raise_for_status()

    async def generate_codes(
        self,
        realm: str,
        user_id: str,
        actor_email: Optional[str] = None
    ) -> Tuple[List[str], List[str]]:
        """
        Generate backup codes, store hashed values, and return plaintext codes.

        Returns:
            (plaintext_codes, hashed_codes)
        """
        plaintext_codes = [secrets.token_hex(4).upper() for _ in range(self.num_codes)]
        hashed_codes = [self._hash_code(code) for code in plaintext_codes]

        async with self.keycloak_admin as kc:
            user = await self._get_user(kc, realm, user_id)
            attributes = user.get("attributes") or {}
            attributes[self.ATTRIBUTE_KEY] = hashed_codes

            await self._save_attributes(kc, realm, user_id, attributes)

        AuditService.log_auth_event(
            realm_name=realm,
            action="backup_codes_generated",
            actor_user_id=user_id,
            actor_email=actor_email,
        )

        logger.info("Generated %d backup codes for user %s in realm %s", self.num_codes, user_id, realm)
        return plaintext_codes, hashed_codes

    async def verify_code(
        self,
        realm: str,
        user_id: str,
        code: str,
        actor_email: Optional[str] = None
    ) -> bool:
        """Verify and consume a backup code."""
        code_hash = self._hash_code(code.strip())

        async with self.keycloak_admin as kc:
            user = await self._get_user(kc, realm, user_id)
            attributes = user.get("attributes") or {}
            stored_hashes: List[str] = attributes.get(self.ATTRIBUTE_KEY) or []

            # Normalize stored hashes to list
            if isinstance(stored_hashes, str):
                stored_hashes = [stored_hashes]

            if code_hash not in stored_hashes:
                logger.warning("Backup code verification failed for user %s (realm=%s)", user_id, realm)
                return False

            # Consume one instance of the code hash (single-use even if duplicates exist)
            remaining = list(stored_hashes)
            if code_hash in remaining:
                remaining.remove(code_hash)
            attributes[self.ATTRIBUTE_KEY] = remaining
            await self._save_attributes(kc, realm, user_id, attributes)

        AuditService.log_auth_event(
            realm_name=realm,
            action="backup_code_used",
            actor_user_id=user_id,
            actor_email=actor_email,
            details={"remaining": len(remaining)},
        )

        logger.info(
            "Backup code verified for user %s in realm %s (remaining=%d)",
            user_id,
            realm,
            len(remaining),
        )
        return True
