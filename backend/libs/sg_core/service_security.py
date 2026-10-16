"""Shared production security posture and internal-service auth helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import ClassVar
from urllib.parse import urlsplit

from fastapi import HTTPException, status
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
]
DEFAULT_INTERNAL_SERVICE_TOKEN = "internal-service-token-change-in-production"
STANDARD_TENANT_HEADER = "X-Tenant-ID"
STANDARD_INTERNAL_TOKEN_HEADER = "Authorization"
LEGACY_INTERNAL_SERVICE_TOKEN_HEADER = "X-Internal-Service-Token"
LEGACY_INTERNAL_TOKEN_HEADER = "X-Internal-Token"
BEARER_PREFIX = "Bearer "
LOCAL_PUBLIC_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
DEFAULT_DATABASE_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "postgres"}
DEFAULT_REDIS_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "redis"}
DEFAULT_KEYCLOAK_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "keycloak"}
DEFAULT_VAULT_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "vault"}
DEFAULT_OPENSEARCH_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "opensearch"}
DEFAULT_DATABASE_CREDENTIALS = {("sg", "sg"), ("postgres", "postgres")}


def normalize_environment(value: object) -> str:
    """Normalize environment strings so services behave consistently."""
    return str(value or "development").strip().lower()


def parse_cors_origins(value: object) -> list[str]:
    """Parse comma-separated CORS allowlists from env/config values."""
    if value is None:
        return DEFAULT_CORS_ORIGINS.copy()
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return DEFAULT_CORS_ORIGINS.copy()


def require_explicit_cors_allowlist(environment: str, cors_origins: list[str]) -> None:
    """Reject wildcard or empty CORS in production."""
    if normalize_environment(environment) != "production":
        return
    if not cors_origins or any(origin == "*" for origin in cors_origins):
        raise ValueError("CORS_ORIGINS must be an explicit allowlist in production")


def require_https_public_origins(environment: str, cors_origins: list[str]) -> None:
    """Reject localhost or non-HTTPS browser origins in production."""
    if normalize_environment(environment) != "production":
        return

    for origin in cors_origins:
        parsed = urlsplit(str(origin).strip())
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme != "https":
            raise ValueError("CORS_ORIGINS must use HTTPS origins in production")
        if hostname in LOCAL_PUBLIC_HOSTS:
            raise ValueError("CORS_ORIGINS cannot contain localhost-style origins in production")


def require_non_default_internal_token(environment: str, token: str | None) -> None:
    """Reject default or missing internal service auth in production."""
    if normalize_environment(environment) != "production":
        return
    if not token or token == DEFAULT_INTERNAL_SERVICE_TOKEN:
        raise ValueError("INTERNAL_SERVICE_TOKEN cannot use the default value in production")


def require_tls_verification(environment: str, enabled: bool, setting_name: str) -> None:
    """Reject disabled TLS verification in production."""
    if normalize_environment(environment) != "production":
        return
    if enabled is not True:
        raise ValueError(f"{setting_name} must be enabled in production")


def require_non_default_database_url(environment: str, database_url: str | None, setting_name: str) -> None:
    """Reject missing or placeholder database URLs in production."""
    if normalize_environment(environment) != "production":
        return

    value = str(database_url or "").strip()
    if not value:
        raise ValueError(f"{setting_name} is required in production")

    parsed = urlsplit(value)
    hostname = (parsed.hostname or "").lower()
    username = parsed.username or ""
    password = parsed.password or ""
    if hostname in DEFAULT_DATABASE_HOSTS:
        raise ValueError(f"{setting_name} cannot point to the default local database host in production")
    if (username, password) in DEFAULT_DATABASE_CREDENTIALS:
        raise ValueError(f"{setting_name} cannot use default database credentials in production")


def require_authenticated_redis_url(environment: str, redis_url: str | None, setting_name: str) -> None:
    """Reject placeholder Redis URLs and unauthenticated Redis in production."""
    if normalize_environment(environment) != "production":
        return

    value = str(redis_url or "").strip()
    if not value:
        raise ValueError(f"{setting_name} is required in production")

    parsed = urlsplit(value)
    hostname = (parsed.hostname or "").lower()
    if hostname in DEFAULT_REDIS_HOSTS:
        raise ValueError(f"{setting_name} cannot point to the default local Redis host in production")
    if not parsed.password:
        raise ValueError(f"{setting_name} must include Redis authentication in production")


def require_secure_service_url(
    environment: str,
    service_url: str | None,
    setting_name: str,
    *,
    disallowed_hosts: set[str] | None = None,
) -> None:
    """Reject missing, non-HTTPS, or placeholder external service URLs in production."""
    if normalize_environment(environment) != "production":
        return

    value = str(service_url or "").strip()
    if not value:
        raise ValueError(f"{setting_name} is required in production")

    parsed = urlsplit(value)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https":
        raise ValueError(f"{setting_name} must use HTTPS in production")
    if hostname in (disallowed_hosts or set()) or hostname in LOCAL_PUBLIC_HOSTS:
        raise ValueError(f"{setting_name} cannot use a localhost or placeholder host in production")


def extract_bearer_token(
    authorization: object,
    *,
    missing_detail: str = "Missing authorization header",
    invalid_detail: str = "Invalid authorization header format",
    missing_status_code: int = status.HTTP_401_UNAUTHORIZED,
    invalid_status_code: int = status.HTTP_401_UNAUTHORIZED,
) -> str | None:
    """Return the bearer token value from an Authorization header."""
    if authorization is None:
        return None

    value = str(authorization).strip()
    if not value:
        raise HTTPException(status_code=missing_status_code, detail=missing_detail)
    if not value.startswith(BEARER_PREFIX):
        raise HTTPException(status_code=invalid_status_code, detail=invalid_detail)

    token = value[len(BEARER_PREFIX):].strip()
    if not token:
        raise HTTPException(status_code=missing_status_code, detail=missing_detail)
    return token


def resolve_internal_service_token(
    *,
    authorization: str | None = None,
    x_internal_service_token: str | None = None,
    x_internal_token: str | None = None,
    missing_detail: str = "Missing internal service token",
    invalid_detail: str = "Invalid authorization header format",
    conflicting_detail: str = "Conflicting internal service authentication headers",
    missing_status_code: int = status.HTTP_401_UNAUTHORIZED,
    invalid_status_code: int = status.HTTP_401_UNAUTHORIZED,
    conflicting_status_code: int = status.HTTP_401_UNAUTHORIZED,
) -> str | None:
    """Resolve a single internal service token from supported headers."""
    candidates: list[tuple[str, str]] = []

    bearer_token = extract_bearer_token(
        authorization,
        missing_detail=missing_detail,
        invalid_detail=invalid_detail,
        missing_status_code=missing_status_code,
        invalid_status_code=invalid_status_code,
    )
    if bearer_token:
        candidates.append((STANDARD_INTERNAL_TOKEN_HEADER, bearer_token))

    for header_name, raw_value in (
        (LEGACY_INTERNAL_SERVICE_TOKEN_HEADER, x_internal_service_token),
        (LEGACY_INTERNAL_TOKEN_HEADER, x_internal_token),
    ):
        if raw_value is None:
            continue
        token = str(raw_value).strip()
        if not token:
            raise HTTPException(status_code=missing_status_code, detail=missing_detail)
        candidates.append((header_name, token))

    if not candidates:
        return None

    unique_tokens = {token for _, token in candidates}
    if len(unique_tokens) > 1:
        raise HTTPException(
            status_code=conflicting_status_code,
            detail=conflicting_detail,
        )

    return candidates[0][1]


def verify_internal_service_token(
    expected_token: str | None,
    *,
    authorization: str | None = None,
    x_internal_service_token: str | None = None,
    x_internal_token: str | None = None,
    missing_detail: str = "Missing internal service token",
    invalid_detail: str = "Invalid internal service token",
    conflicting_detail: str = "Conflicting internal service authentication headers",
    missing_status_code: int = status.HTTP_401_UNAUTHORIZED,
    invalid_status_code: int = status.HTTP_401_UNAUTHORIZED,
    conflicting_status_code: int = status.HTTP_401_UNAUTHORIZED,
) -> str:
    """Verify the configured internal service token from the supported headers."""
    token = resolve_internal_service_token(
        authorization=authorization,
        x_internal_service_token=x_internal_service_token,
        x_internal_token=x_internal_token,
        missing_detail=missing_detail,
        invalid_detail="Invalid authorization header format",
        conflicting_detail=conflicting_detail,
        missing_status_code=missing_status_code,
        invalid_status_code=invalid_status_code,
        conflicting_status_code=conflicting_status_code,
    )
    if token is None:
        raise HTTPException(status_code=missing_status_code, detail=missing_detail)
    if not expected_token or token != expected_token:
        raise HTTPException(status_code=invalid_status_code, detail=invalid_detail)
    return token


def build_internal_auth_headers(
    token: str,
    *,
    tenant_id: object | None = None,
    extra_headers: Mapping[str, object] | None = None,
) -> dict[str, str]:
    """Build canonical headers for service-to-service calls."""
    headers: dict[str, str] = {}
    if extra_headers:
        for key, value in extra_headers.items():
            if value is None:
                continue
            text = str(value).strip()
            if text:
                headers[str(key)] = text

    headers[STANDARD_INTERNAL_TOKEN_HEADER] = f"{BEARER_PREFIX}{token}"
    if tenant_id is not None:
        headers[STANDARD_TENANT_HEADER] = str(tenant_id)
    return headers


class ServiceSecuritySettings(BaseSettings):
    """Base settings model that enforces consistent service security defaults."""

    ENVIRONMENT: str = "development"
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: DEFAULT_CORS_ORIGINS.copy())
    INTERNAL_SERVICE_TOKEN: str | None = DEFAULT_INTERNAL_SERVICE_TOKEN
    UPSTREAM_TLS_VERIFY: bool = False

    REQUIRE_CORS_ALLOWLIST_IN_PROD: ClassVar[bool] = True
    REQUIRE_INTERNAL_TOKEN_IN_PROD: ClassVar[bool] = False
    REQUIRE_UPSTREAM_TLS_VERIFY_IN_PROD: ClassVar[bool] = False

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def _normalize_environment(cls, value: object) -> str:
        return normalize_environment(value)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> list[str]:
        return parse_cors_origins(value)

    @model_validator(mode="after")
    def _validate_security_posture(self):
        if self.REQUIRE_CORS_ALLOWLIST_IN_PROD:
            require_explicit_cors_allowlist(self.ENVIRONMENT, self.CORS_ORIGINS)

        if self.REQUIRE_INTERNAL_TOKEN_IN_PROD:
            require_non_default_internal_token(self.ENVIRONMENT, self.INTERNAL_SERVICE_TOKEN)

        if self.REQUIRE_UPSTREAM_TLS_VERIFY_IN_PROD:
            require_tls_verification(
                self.ENVIRONMENT,
                self.UPSTREAM_TLS_VERIFY,
                "UPSTREAM_TLS_VERIFY",
            )

        return self
