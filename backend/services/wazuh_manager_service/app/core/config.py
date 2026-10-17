"""Configuration for Wazuh Manager Service."""

import os
from pydantic import Field, model_validator
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.user_principals import UserClientBinding
from app.core.principal_policy import WazuhPrincipalSettings, WazuhInventoryReader
from typing import Optional

from sg_core.service_security import ServiceSecuritySettings


class Settings(ServiceSecuritySettings):
    """Application settings."""

    REQUIRE_INTERNAL_TOKEN_IN_PROD = True
    REQUIRE_UPSTREAM_TLS_VERIFY_IN_PROD = True

    # Service info
    SERVICE_NAME: str = "wazuh-manager-service"
    VERSION: str = "1.0.0"

    # Database configuration
    DB_URL: str = os.getenv("DB_URL", "postgresql://sg:sg@postgres:5432/sg")

    # Wazuh Manager API configuration
    WAZUH_MANAGER_URL: str = os.getenv(
        "WAZUH_MANAGER_URL", "http://wazuh-manager:55000"
    )
    WAZUH_API_USERNAME: str = os.getenv("WAZUH_API_USERNAME", "wazuh-api")
    WAZUH_API_PASSWORD: str = os.getenv("WAZUH_API_PASSWORD", "MyS3cr3tP455w0rd!")

    # IAM Agent (for token validation)
    IAM_AGENT_URL: str = os.getenv("IAM_AGENT_URL", "http://iam_agent:8000")

    # Keycloak configuration (for direct validation if needed)
    KEYCLOAK_URL: str = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
    KEYCLOAK_REALM: str = os.getenv("KEYCLOAK_REALM", "sentinelgrid")

    KEYCLOAK_CLIENT_ID: str = "sentinelgrid-web"
    IAM_TOKEN_VALIDATION_TIMEOUT: float = Field(
        default=5.0, gt=0, le=10, allow_inf_nan=False
    )
    IAM_VERIFIER_CA_BUNDLE: str | None = None
    IAM_USER_CLIENT_BINDINGS: tuple[UserClientBinding, ...] = Field(
        default=(), max_length=256
    )
    WAZUH_INVENTORY_READERS: tuple[WazuhInventoryReader, ...] = Field(
        default=(), max_length=256
    )

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

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

    def principal_settings(self) -> WazuhPrincipalSettings:
        return WazuhPrincipalSettings(
            _env_file=None,
            ENVIRONMENT=self.ENVIRONMENT,
            IAM_USER_CLIENT_BINDINGS=self.IAM_USER_CLIENT_BINDINGS,
            WAZUH_INVENTORY_READERS=self.WAZUH_INVENTORY_READERS,
        )


settings = Settings()
