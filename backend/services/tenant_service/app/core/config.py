"""Configuration for Tenant Service."""

import os
from typing import Optional

from pydantic import model_validator

from sg_core.service_security import (
    ServiceSecuritySettings,
    require_tls_verification,
)

DEFAULT_KEYCLOAK_ADMIN_PASSWORD = "admin"
DEFAULT_KEYCLOAK_ADMIN_CLIENT_ID = "sentinelgrid-tenant-service"


class Settings(ServiceSecuritySettings):
    """Application settings."""

    REQUIRE_INTERNAL_TOKEN_IN_PROD = True
    
    # Service info
    SERVICE_NAME: str = "tenant-service"
    VERSION: str = "0.1.0"
    
    # Database configuration
    DB_HOST: str = os.getenv("DB_HOST", "postgres")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "sg")
    DB_USER: str = os.getenv("DB_USER", "sg")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "sg")
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL from components."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    KEYCLOAK_VERIFY_TLS: bool = os.getenv("KEYCLOAK_VERIFY_TLS", "false").lower() == "true"

    # Keycloak configuration
    KEYCLOAK_URL: str = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
    KEYCLOAK_ADMIN_USER: str = os.getenv("KEYCLOAK_ADMIN_USER", "admin")
    KEYCLOAK_ADMIN_PASSWORD: str = os.getenv("KEYCLOAK_ADMIN_PASSWORD", DEFAULT_KEYCLOAK_ADMIN_PASSWORD)
    KEYCLOAK_ADMIN_TOKEN_REALM: str = os.getenv("KEYCLOAK_ADMIN_TOKEN_REALM", "master")
    KEYCLOAK_ADMIN_CLIENT_ID: str = os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", DEFAULT_KEYCLOAK_ADMIN_CLIENT_ID)
    KEYCLOAK_ADMIN_CLIENT_SECRET: Optional[str] = os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET")
    KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT: bool = os.getenv("KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT", "false").lower() == "true"
    KEYCLOAK_REALM_TEMPLATE: str = os.getenv("KEYCLOAK_REALM_TEMPLATE", "sentinelgrid")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"
    
    @model_validator(mode="after")
    def _validate_security_posture(self):
        super()._validate_security_posture()

        if self.ENVIRONMENT == "production":
            if self.KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT:
                if not self.KEYCLOAK_ADMIN_CLIENT_SECRET:
                    raise ValueError("KEYCLOAK_ADMIN_CLIENT_SECRET is required when KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT is enabled")
            elif self.KEYCLOAK_ADMIN_PASSWORD == DEFAULT_KEYCLOAK_ADMIN_PASSWORD:
                raise ValueError("KEYCLOAK_ADMIN_PASSWORD cannot use the default value in production")
            require_tls_verification(self.ENVIRONMENT, self.KEYCLOAK_VERIFY_TLS, "KEYCLOAK_VERIFY_TLS")

        return self


settings = Settings()
