"""Configuration settings for API Gateway."""

from typing import List

from pydantic import field_validator, model_validator
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

        return self


settings = Settings()
