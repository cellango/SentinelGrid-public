"""Verify Keycloak access tokens against configured issuers and RSA keys."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import re
import time
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

from app.core.config import settings
from app.services.keycloak_client import KeycloakClient

logger = logging.getLogger(__name__)
_REALM = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")


class TokenValidator:
    """The unverified issuer selects only among explicitly configured origins.

    Only the configured internal Keycloak URL supplies keys. Untrusted issuer,
    jku/x5u and embedded JWK values can never supply a key or network destination.
    """

    def __init__(self, keycloak_client: KeycloakClient):
        self.keycloak_client = keycloak_client
        self.default_realm = settings.KEYCLOAK_REALM
        self.realm = self.default_realm  # compatibility for existing callers
        self.server_url = settings.KEYCLOAK_URL.rstrip("/")
        self.cache_ttl = settings.JWKS_CACHE_TTL
        self.jwks_cache: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _invalid(error: str) -> dict[str, Any]:
        return dict(valid=False, error=error, payload=None, tenant_id=None,
                    user_id=None, username=None, email=None, roles=[], expires_at=None)

    def _issuer_and_realm(self, token: str) -> tuple[str, str]:
        # Routing hints only. No identity/tenant is trusted until jwt.decode below.
        if not isinstance(token, str) or len(token) > 32768 or token.count(".") != 2:
            raise ValueError("Invalid token format")
        parts = token.split(".")
        import base64
        claims = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
        issuer = claims.get("iss") if isinstance(claims, dict) else None
        if not isinstance(issuer, str):
            raise ValueError("Missing token issuer")
        parsed = urlsplit(issuer)
        if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Invalid token issuer")
        bases = {self.server_url}
        bases.update(v.rstrip("/") for v in getattr(settings, "KEYCLOAK_ISSUER_BASE_URLS", []) if v)
        for base in bases:
            prefix = base + "/realms/"
            if issuer.startswith(prefix):
                realm = issuer[len(prefix):]
                if _REALM.fullmatch(realm):
                    return issuer, realm
        raise ValueError("Untrusted token issuer")

    def _extract_realm_from_token(self, token: str) -> str | None:
        try:
            return self._issuer_and_realm(token)[1]
        except (ValueError, TypeError, UnicodeError):
            return None

    def _get_jwks_for_realm(self, realm: str, issuer_url: str | None = None) -> dict | None:
        if not _REALM.fullmatch(realm):
            return None
        cached = self.jwks_cache.get(realm)
        if cached and time.monotonic() - cached["timestamp"] < self.cache_ttl:
            return cached["jwks"]
        try:
            with httpx.Client(timeout=settings.TOKEN_VALIDATION_TIMEOUT,
                              verify=settings.KEYCLOAK_VERIFY_TLS,
                              follow_redirects=False) as client:
                response = client.get(f"{self.server_url}/realms/{realm}/protocol/openid-connect/certs")
                response.raise_for_status()
                value = response.json()
            if not isinstance(value, dict) or not isinstance(value.get("keys"), list):
                return None
            # Bounded per-instance cache; arbitrary realm names cannot grow it forever.
            if len(self.jwks_cache) >= 128:
                oldest = min(self.jwks_cache, key=lambda k: self.jwks_cache[k]["timestamp"])
                self.jwks_cache.pop(oldest)
            self.jwks_cache[realm] = dict(jwks=value, timestamp=time.monotonic())
            return value
        except (httpx.HTTPError, ValueError, TypeError):
            logger.warning("Unable to load trusted signing keys")
            return None

    def _get_jwks(self):
        return self._get_jwks_for_realm(self.default_realm)

    def _get_signing_key_from_jwks(self, token: str, jwks: dict):
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str) or not header["kid"]:
                return None
            if any(k in header for k in ("jku", "x5u", "jwk", "crit")):
                return None
            keys = [k for k in jwks.get("keys", []) if isinstance(k, dict)
                    and k.get("kid") == header["kid"] and k.get("kty") == "RSA"
                    and k.get("use", "sig") == "sig" and k.get("alg", "RS256") == "RS256"
                    and ("key_ops" not in k or (isinstance(k["key_ops"], list) and "verify" in k["key_ops"]))]
            if len(keys) != 1:
                return None
            return RSAAlgorithm.from_jwk(json.dumps(keys[0]))
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            return None

    def _get_signing_key(self, token, jwks):
        return self._get_signing_key_from_jwks(token, jwks)

    def validate_token(self, token: str) -> dict[str, Any]:
        try:
            issuer, realm = self._issuer_and_realm(token)
            jwks = self._get_jwks_for_realm(realm, issuer)
            if jwks is None:
                return self._invalid("Trusted signing keys unavailable")
            key = self._get_signing_key_from_jwks(token, jwks)
            if key is None:
                return self._invalid("Invalid token signing key or algorithm")
            payload = jwt.decode(token, key, algorithms=["RS256"],
                                 audience=settings.KEYCLOAK_CLIENT_ID, issuer=issuer,
                                 options={"require": ["exp", "iat", "iss", "aud", "sub", "tenant_id"]})
            # Numeric dates cannot be booleans or coercible strings. PyJWT checks time.
            for name in ("exp", "iat", "nbf"):
                if name in payload and (isinstance(payload[name], bool) or not isinstance(payload[name], (int, float))):
                    raise ValueError("Invalid token time claim")
            if not isinstance(payload["tenant_id"], str):
                raise ValueError("Invalid tenant claim")
            tenant_id = str(UUID(payload["tenant_id"]))
            if not isinstance(payload["sub"], str) or not payload["sub"]:
                raise ValueError("Invalid token subject")
            access = payload.get("realm_access", {})
            roles = access.get("roles", []) if isinstance(access, dict) else None
            if not isinstance(roles, list) or not all(isinstance(r, str) for r in roles):
                raise ValueError("Invalid token roles")
            return dict(valid=True, error=None, payload=payload, tenant_id=tenant_id,
                        user_id=payload["sub"], username=payload.get("preferred_username") or payload.get("username"),
                        email=payload.get("email"), roles=roles,
                        expires_at=datetime.fromtimestamp(payload["exp"], timezone.utc))
        except (jwt.PyJWTError, ValueError, TypeError, KeyError, UnicodeError, OverflowError):
            # Never re-decode as authenticated after signature/issuer/claim failures.
            return self._invalid("Invalid or expired token")

    def introspect_token(self, token: str) -> dict[str, Any]:
        # Introspection cannot bypass the same signature/issuer/tenant boundary.
        validation = self.validate_token(token)
        if not validation["valid"]:
            return dict(active=False, sub=None, tenant_id=None, username=None, email=None,
                        realm_access=None, roles=[], exp=None, iat=None, error=validation["error"])
        try:
            remote = self.keycloak_client.introspect_token(token)
        except Exception:
            remote = None
        # Preserve offline signed-token fallback only for an unavailable result.
        if isinstance(remote, dict) and remote.get("active") is not True:
            return dict(active=False, sub=None, tenant_id=None, username=None, email=None,
                        realm_access=None, roles=[], exp=None, iat=None, error="Token is not active")
        payload = validation["payload"]
        return dict(active=True, sub=validation["user_id"], tenant_id=validation["tenant_id"],
                    username=validation["username"], email=validation["email"],
                    realm_access={"roles": validation["roles"]}, roles=validation["roles"],
                    exp=payload["exp"], iat=payload["iat"], error=None)
