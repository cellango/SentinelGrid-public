"""Configuration settings for API Gateway."""

from typing import List

from pydantic import Field, field_validator, model_validator
from app.core.ingress import IngressPolicy
from app.core.rate_limit import RateLimitPolicy
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.user_principals import UserClientBinding, UserPrincipalSettings
from pydantic_settings import BaseSettings, SettingsConfigDict

from sg_core.service_security import (
    DEFAULT_INTERNAL_SERVICE_TOKEN,
    DEFAULT_KEYCLOAK_HOSTS,
    normalize_environment,
    parse_cors_origins,
    require_explicit_cors_allowlist,
    require_https_public_origins,
    require_non_default_database_url,
    require_non_default_internal_token,
    require_secure_service_url,
    require_tls_verification,
)


DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
]
DEFAULT_UPSTREAM_TLS_VERIFY = False


class Settings(BaseSettings):
    """API Gateway settings."""

    ENVIRONMENT: str = "development"

    # CORS
    CORS_ORIGINS: List[str] = DEFAULT_CORS_ORIGINS.copy()

    # Service URLs
    ORCHESTRATOR_URL: str = "http://orchestrator:8000"
    SCANNER_ORCHESTRATOR_URL: str = "http://scanner_orchestrator:8000"
    IAM_AGENT_URL: str = "http://iam_agent:8000"
    SIEM_AGENT_URL: str = "http://siem_agent:8000"
    REPORTING_SERVICE_URL: str = "http://reporting_service:8000"
    COMPLIANCE_SERVICE_URL: str = "http://compliance_service:8000"
    AUDIT_SERVICE_URL: str = "http://audit_service:8000"
    SOAR_AGENT_URL: str = "http://soar_agent:8000"
    TICKETING_SERVICE_URL: str = "http://ticketing_service:8000"
    MODEL_GATEWAY_URL: str = "http://model_gateway:8000"
    AGENT_RUNTIME_URL: str = "http://agent_runtime:8000"

    IAM_TOKEN_VALIDATION_TIMEOUT: float = Field(default=5.0, gt=0, le=10, allow_inf_nan=False)
    IAM_VERIFIER_CA_BUNDLE: str | None = None
    IAM_USER_CLIENT_BINDINGS: tuple[UserClientBinding, ...] = Field(default=(), max_length=256)

    MAX_REQUEST_BODY_BYTES: int = Field(default=2 * 1024 * 1024, ge=1, le=64 * 1024 * 1024)
    MAX_UPSTREAM_RESPONSE_BYTES: int = Field(default=2 * 1024 * 1024, ge=1, le=64 * 1024 * 1024)
    REQUEST_BODY_TIMEOUT: float = Field(default=10.0, gt=0, le=60, allow_inf_nan=False)
    MAX_CONCURRENT_REQUESTS: int = Field(default=128, ge=1, le=4096)

    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_FAIL_CLOSED: bool = True
    RATE_LIMIT_REDIS_URL: str = "redis://redis:6379/0"
    RATE_LIMIT_NAMESPACE: str = "sentinelgrid-gateway"
    RATE_LIMIT_RPM_PEER: int = Field(default=600, ge=1, le=1000000)
    RATE_LIMIT_RPM_TENANT: int = Field(default=1200, ge=1, le=1000000)
    RATE_LIMIT_RPM_SUBJECT: int = Field(default=120, ge=1, le=1000000)
    TRUSTED_PROXY_CIDRS: tuple[str, ...] = ()

    # Database
    DB_URL: str = "postgresql://sg:sg@postgres:5432/sg"

    # Keycloak
    KEYCLOAK_URL: str = "http://keycloak:8080"
    KEYCLOAK_REALM: str = "sentinelgrid"
    KEYCLOAK_CLIENT_ID: str = "sentinelgrid-web"

    # Internal Service Token (for service-to-service communication)
    INTERNAL_SERVICE_TOKEN: str = DEFAULT_INTERNAL_SERVICE_TOKEN
    UPSTREAM_TLS_VERIFY: bool = DEFAULT_UPSTREAM_TLS_VERIFY

    # Compliance rollout flags. The gateway exposes these as fallback capability
    # metadata when the compliance service is unavailable.
    COMPLIANCE_MULTI_FRAMEWORK_ENABLED: bool = False
    COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED: bool = False
    COMPLIANCE_AGENT_ENABLED: bool = False

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def _normalize_environment(cls, value):
        return normalize_environment(value)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value):
        return parse_cors_origins(value)

    @model_validator(mode="after")
    def _validate_security_posture(self):
        require_explicit_cors_allowlist(self.ENVIRONMENT, self.CORS_ORIGINS)
        require_https_public_origins(self.ENVIRONMENT, self.CORS_ORIGINS)
        require_non_default_internal_token(self.ENVIRONMENT, self.INTERNAL_SERVICE_TOKEN)
        require_tls_verification(self.ENVIRONMENT, self.UPSTREAM_TLS_VERIFY, "UPSTREAM_TLS_VERIFY")
        require_non_default_database_url(self.ENVIRONMENT, self.DB_URL, "DB_URL")
        require_secure_service_url(
            self.ENVIRONMENT,
            self.KEYCLOAK_URL,
            "KEYCLOAK_URL",
            disallowed_hosts=DEFAULT_KEYCLOAK_HOSTS,
        )

        self.rate_limit_policy()
        if self.ENVIRONMENT not in {"development", "test"}:
            if not self.RATE_LIMIT_ENABLED or not self.RATE_LIMIT_FAIL_CLOSED or not self.RATE_LIMIT_REDIS_URL.startswith("rediss://"):
                raise ValueError("Non-development ingress requires TLS Redis and fail-closed rate limiting")
        self.verification_settings()
        self.user_principal_settings()
        return self


    def rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(enabled=self.RATE_LIMIT_ENABLED, fail_closed=self.RATE_LIMIT_FAIL_CLOSED,
            redis_url=self.RATE_LIMIT_REDIS_URL, namespace=self.RATE_LIMIT_NAMESPACE,
            peer_rpm=self.RATE_LIMIT_RPM_PEER, tenant_rpm=self.RATE_LIMIT_RPM_TENANT,
            subject_rpm=self.RATE_LIMIT_RPM_SUBJECT, trusted_proxy_cidrs=self.TRUSTED_PROXY_CIDRS)

    def ingress_policy(self) -> IngressPolicy:
        return IngressPolicy(allowed_origins=tuple(self.CORS_ORIGINS), max_body_bytes=self.MAX_REQUEST_BODY_BYTES,
                             body_timeout_seconds=self.REQUEST_BODY_TIMEOUT, max_concurrent_requests=self.MAX_CONCURRENT_REQUESTS)

    def verification_settings(self) -> IAMVerificationSettings:
        names = {"ENVIRONMENT", "IAM_AGENT_URL", "KEYCLOAK_CLIENT_ID",
                 "IAM_TOKEN_VALIDATION_TIMEOUT", "IAM_VERIFIER_CA_BUNDLE"}
        return IAMVerificationSettings(_env_file=None, **self.model_dump(include=names))

    def user_principal_settings(self) -> UserPrincipalSettings:
        return UserPrincipalSettings(_env_file=None, ENVIRONMENT=self.ENVIRONMENT, IAM_USER_CLIENT_BINDINGS=self.IAM_USER_CLIENT_BINDINGS)


settings = Settings()
