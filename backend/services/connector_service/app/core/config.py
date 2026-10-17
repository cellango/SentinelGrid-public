"""Configuration for Connector Service."""

import os
from typing import Optional
from pydantic import Field, model_validator
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.user_principals import UserClientBinding
from app.core.principal_policy import ConnectorPrincipalSettings, ConnectorReader

from sg_core.service_security import ServiceSecuritySettings


class Settings(ServiceSecuritySettings):
    """Application settings."""

    REQUIRE_INTERNAL_TOKEN_IN_PROD = True
    
    # Service info
    SERVICE_NAME: str = "connector-service"
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
    
    IAM_AGENT_URL: str = "http://iam_agent:8000"
    KEYCLOAK_CLIENT_ID: str = "sentinelgrid-web"
    IAM_TOKEN_VALIDATION_TIMEOUT: float = Field(default=5.0, gt=0, le=10, allow_inf_nan=False)
    IAM_VERIFIER_CA_BUNDLE: str | None = None
    IAM_USER_CLIENT_BINDINGS: tuple[UserClientBinding, ...] = Field(default=(), max_length=256)
    CONNECTOR_METADATA_READERS: tuple[ConnectorReader, ...] = Field(default=(), max_length=256)

    # Ingestion Service configuration
    INGESTION_SERVICE_URL: str = os.getenv("INGESTION_SERVICE_URL", "http://ingestion_service:8000")
    # Sync configuration
    SYNC_INTERVAL_MINUTES: int = int(os.getenv("SYNC_INTERVAL_MINUTES", "15"))
    SYNC_BATCH_SIZE: int = int(os.getenv("SYNC_BATCH_SIZE", "100"))
    
    # Google Workspace configuration
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8005/auth/google/callback")
    
    # AWS configuration (for cloud connectors)
    AWS_DEFAULT_REGION: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    
    # Encryption key for credentials (in production, use proper key management)
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "change-me-in-production-32-chars!")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"
    
    @model_validator(mode="after")
    def _validate_owned_identity(self):
        self.verification_settings()
        self.principal_settings()
        return self

    def verification_settings(self) -> IAMVerificationSettings:
        names = {"ENVIRONMENT", "IAM_AGENT_URL", "KEYCLOAK_CLIENT_ID", "IAM_TOKEN_VALIDATION_TIMEOUT", "IAM_VERIFIER_CA_BUNDLE"}
        return IAMVerificationSettings(_env_file=None, **self.model_dump(include=names))

    def principal_settings(self) -> ConnectorPrincipalSettings:
        return ConnectorPrincipalSettings(_env_file=None, ENVIRONMENT=self.ENVIRONMENT,
            IAM_USER_CLIENT_BINDINGS=self.IAM_USER_CLIENT_BINDINGS, CONNECTOR_METADATA_READERS=self.CONNECTOR_METADATA_READERS)


settings = Settings()
