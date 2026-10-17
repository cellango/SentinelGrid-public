"""Delegated JWT verification over an operator-owned IAM transport.

Parsing the submitted JWT below binds the IAM receipt to that input. It never
authenticates a claim: only a successful response from the configured IAM service
can do that. This module does not grant actions or classify a principal as human.
"""

from __future__ import annotations

import base64
from datetime import datetime
from functools import lru_cache
import json
import math
import re
import ssl
import time
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import HTTPException
import httpx
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOCAL_IAM_HOSTS = {"iam_agent", "localhost", "127.0.0.1", "::1"}
_SEGMENT = re.compile(r"[A-Za-z0-9_-]+\Z")
_MAX_TOKEN = 32768
_MAX_RESPONSE = 131072
_UNAVAILABLE = "Token verification service unavailable"


class IAMVerificationSettings(BaseSettings):
    """Process configuration, never request/claim/header-selected destinations."""

    ENVIRONMENT: str = "development"
    IAM_AGENT_URL: str = "http://iam_agent:8000"
    KEYCLOAK_CLIENT_ID: str = "sentinelgrid-web"
    IAM_TOKEN_VALIDATION_TIMEOUT: float = Field(default=5.0, gt=0, le=10, allow_inf_nan=False)
    IAM_VERIFIER_CA_BUNDLE: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore", frozen=True,
        hide_input_in_errors=True,
    )

    @model_validator(mode="after")
    def validate_destination(self):
        value = self.IAM_AGENT_URL
        parsed = urlsplit(value)
        if (
            value != value.strip() or any(ord(c) < 33 or ord(c) == 127 for c in value)
            or "\\" in value or "%" in value
            or parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
            or "?" in value or "#" in value
        ):
            raise ValueError("IAM_AGENT_URL must be an HTTP(S) origin without credentials or suffixes")
        if parsed.port == 0:
            raise ValueError("IAM_AGENT_URL must use a valid port")
        environment = self.ENVIRONMENT.strip().lower()
        if parsed.scheme == "http" and not (
            environment in {"development", "test"} and parsed.hostname in _LOCAL_IAM_HOSTS
        ):
            raise ValueError("IAM verification requires HTTPS outside owned local development")
        if environment not in {"development", "test"} and parsed.hostname in _LOCAL_IAM_HOSTS:
            raise ValueError("IAM verification requires a non-placeholder production origin")
        if not self.KEYCLOAK_CLIENT_ID or self.KEYCLOAK_CLIENT_ID != self.KEYCLOAK_CLIENT_ID.strip():
            raise ValueError("KEYCLOAK_CLIENT_ID must name the IAM verifier's audience")
        if self.IAM_VERIFIER_CA_BUNDLE is not None and not self.IAM_VERIFIER_CA_BUNDLE.strip():
            raise ValueError("IAM_VERIFIER_CA_BUNDLE must be an explicit CA file")
        return self


@lru_cache(maxsize=1)
def get_verification_settings() -> IAMVerificationSettings:
    """Resolve owned settings lazily; reload requires a process restart."""
    return IAMVerificationSettings()


def _invalid() -> HTTPException:
    return HTTPException(status_code=401, detail="Invalid token")


def _unique_object(pairs):
    value = {}
    for name, item in pairs:
        if name in value:
            raise ValueError("Duplicate JSON field")
        value[name] = item
    return value


def _reject_constant(value):
    raise ValueError("Non-finite JSON number")


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Non-finite JSON number")
    return number


def _json(data: bytes) -> dict:
    value = json.loads(data, object_pairs_hook=_unique_object, parse_constant=_reject_constant, parse_float=_finite_float)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def _submitted_claims(token: str) -> dict:
    if not isinstance(token, str) or not 1 <= len(token) <= _MAX_TOKEN:
        raise ValueError("Invalid token size")
    parts = token.split(".")
    if len(parts) != 3 or not all(_SEGMENT.fullmatch(p) for p in parts):
        raise ValueError("Expected a compact signed JWT")
    decoded = []
    for part in parts:
        value = base64.b64decode(part + "=" * (-len(part) % 4), altchars=b"-_", validate=True)
        if base64.urlsafe_b64encode(value).decode().rstrip("=") != part:
            raise ValueError("Non-canonical token encoding")
        decoded.append(value)
    header = _json(decoded[0])
    if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str) or not header["kid"]:
        raise ValueError("Unsupported signing key or algorithm")
    if any(k in header for k in ("jku", "x5u", "jwk", "crit")):
        raise ValueError("Untrusted key source")
    return _json(decoded[1])


def _uuid(value) -> str:
    if not isinstance(value, str):
        raise ValueError("Expected UUID string")
    parsed = UUID(value)
    if parsed.int == 0:
        raise ValueError("Nil identity")
    return str(parsed)


def _roles(value) -> list[str]:
    if (
        not isinstance(value, list) or len(value) > 128
        or not all(isinstance(r, str) and 0 < len(r) <= 256 and r == r.strip()
                   and all(ord(c) >= 32 and ord(c) != 127 for c in r) for r in value)
        or len(set(value)) != len(value)
    ):
        raise ValueError("Malformed roles")
    return value


def _receipt(result: dict, submitted: dict, audience: str) -> dict:
    if result.get("valid") is False:
        raise _invalid()
    if result.get("valid") is not True or result.get("error") is not None:
        raise ValueError("Malformed verification result")
    payload = result.get("payload")
    # Compare JSON types as well as values (Python considers True == 1).
    if not isinstance(payload, dict) or json.dumps(payload, sort_keys=True) != json.dumps(submitted, sort_keys=True):
        raise ValueError("Verification receipt belongs to different claims")
    tenant = _uuid(payload.get("tenant_id"))
    subject = _uuid(payload.get("sub"))
    if _uuid(result.get("tenant_id")) != tenant or _uuid(result.get("user_id")) != subject:
        raise ValueError("Conflicting verified identity")
    access = payload.get("realm_access", {})
    if not isinstance(access, dict):
        raise ValueError("Malformed realm access")
    roles = _roles(access.get("roles", []))
    if _roles(result.get("roles")) != roles:
        raise ValueError("Conflicting verified roles")
    for name, expected in (("user_id", subject), ("roles", roles), ("realm_roles", roles)):
        if name in payload and payload[name] != expected:
            raise ValueError("Conflicting identity alias")
    if result.get("plan_tier") is not None and result["plan_tier"] != payload.get("plan_tier"):
        raise ValueError("Unsigned plan enrichment")
    if not isinstance(payload.get("iss"), str) or not payload["iss"]:
        raise ValueError("Missing verified issuer")
    aud = payload.get("aud")
    if isinstance(aud, str):
        aud = [aud]
    if not isinstance(aud, list) or not all(isinstance(a, str) for a in aud) or audience not in aud:
        raise ValueError("Wrong verifier audience")
    now = time.time()
    for name in ("exp", "iat", "nbf"):
        value = payload.get(name)
        if name == "nbf" and name not in payload:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("Invalid verified token time")
    if payload["exp"] <= now or payload["iat"] > now or payload["exp"] <= payload["iat"] or payload.get("nbf", 0) > now:
        raise _invalid()
    expires = result.get("expires_at")
    if not isinstance(expires, str):
        raise ValueError("Missing verified expiry")
    expires = datetime.fromisoformat(expires)
    if expires.tzinfo is None or abs(expires.timestamp() - payload["exp"]) > 0.001:
        raise ValueError("Conflicting verified expiry")
    # New dictionary; no mutation or summary override of the verified payload.
    return {**payload, "tenant_id": tenant, "sub": subject, "user_id": subject, "roles": roles.copy()}


def verify_iam_token(token: str, *, config: IAMVerificationSettings | None = None) -> dict:
    """Obtain a bounded, input-bound receipt. Never fall back to decoding locally."""
    if token is None or token == "":
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        submitted = _submitted_claims(token)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise _invalid() from None
    try:
        config = config if config is not None else get_verification_settings()
        verify = ssl.create_default_context(cafile=config.IAM_VERIFIER_CA_BUNDLE) if config.IAM_VERIFIER_CA_BUNDLE else True
        with httpx.Client(
            timeout=httpx.Timeout(config.IAM_TOKEN_VALIDATION_TIMEOUT, pool=1.0),
            verify=verify, trust_env=False, follow_redirects=False,
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
        ) as client:
            with client.stream(
                "POST", config.IAM_AGENT_URL.rstrip("/") + "/internal/iam/auth/validate-token",
                json={"token": token}, headers={"Accept": "application/json"},
            ) as response:
                if response.status_code in {401, 403}:
                    raise _invalid()
                if response.status_code != 200 or response.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
                    raise ValueError("Invalid verification response")
                body = bytearray()
                for chunk in response.iter_bytes(chunk_size=8192):
                    body.extend(chunk)
                    if len(body) > _MAX_RESPONSE:
                        raise ValueError("Verification response too large")
                result = _json(bytes(body))
        return _receipt(result, submitted, config.KEYCLOAK_CLIENT_ID)
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError, TypeError, OSError, OverflowError, RecursionError):
        # Never return tokens, response bodies, identities, URLs or raw exceptions.
        raise HTTPException(status_code=503, detail=_UNAVAILABLE) from None
