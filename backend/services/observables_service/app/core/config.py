"""Configuration for Observables Service."""

import os
from pydantic import Field, model_validator
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.user_principals import UserClientBinding
from app.core.principal_policy import ObservablePrincipalSettings, ObservableReader
from typing import Optional

from sg_core.service_security import ServiceSecuritySettings


class Settings(ServiceSecuritySettings):
    """Application settings."""

    REQUIRE_INTERNAL_TOKEN_IN_PROD = True

    # Service info
    SERVICE_NAME: str = "observables-service"
    VERSION: str = "0.1.0"

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "sg")
    DB_USER: str = os.getenv("DB_USER", "sg")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "sg")

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Cortex
    CORTEX_URL: str = os.getenv("CORTEX_URL", "http://cortex:9001")
    CORTEX_API_KEY: Optional[str] = os.getenv("CORTEX_API_KEY")

    # IAM Agent
    IAM_AGENT_URL: str = os.getenv("IAM_AGENT_URL", "http://iam_agent:8000")

    KEYCLOAK_CLIENT_ID: str = "sentinelgrid-web"
    IAM_TOKEN_VALIDATION_TIMEOUT: float = Field(
        default=5.0, gt=0, le=10, allow_inf_nan=False
    )
    IAM_VERIFIER_CA_BUNDLE: str | None = None
    IAM_USER_CLIENT_BINDINGS: tuple[UserClientBinding, ...] = Field(
        default=(), max_length=256
    )
    OBSERVABLE_READERS: tuple[ObservableReader, ...] = Field(default=(), max_length=256)

    # Enrichment settings
    ENRICHMENT_TTL_HOURS: int = int(os.getenv("ENRICHMENT_TTL_HOURS", "24"))
    AUTO_ENRICH: bool = os.getenv("AUTO_ENRICH", "true").lower() == "true"

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "false").lower() == "true"

    @model_validator(mode="after")
    def _validate_owned_identity(self):
        self.verification_settings()
        self.principal_settings()
        return self

    def verification_settings(self) -> IAMVerificationSettings:
        names = {
            "ENVIRONMENT",
            "IAM_AGENT_URL",
            "KEYCLOAK_CLIENT_ID",
            "IAM_TOKEN_VALIDATION_TIMEOUT",
            "IAM_VERIFIER_CA_BUNDLE",
        }
        return IAMVerificationSettings(_env_file=None, **self.model_dump(include=names))

    def principal_settings(self) -> ObservablePrincipalSettings:
        return ObservablePrincipalSettings(
            _env_file=None,
            ENVIRONMENT=self.ENVIRONMENT,
            IAM_USER_CLIENT_BINDINGS=self.IAM_USER_CLIENT_BINDINGS,
            OBSERVABLE_READERS=self.OBSERVABLE_READERS,
        )


settings = Settings()
