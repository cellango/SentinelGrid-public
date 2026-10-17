"""Configuration for Ingestion Service."""

import os
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import SettingsConfigDict
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.user_principals import UserClientBinding
from app.core.principal_policy import IngestionPrincipalSettings, RuntimeReader

from sg_core.service_security import ServiceSecuritySettings


class Settings(ServiceSecuritySettings):
    """Application settings."""
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
    REQUIRE_INTERNAL_TOKEN_IN_PROD = True
    
    # Service info
    SERVICE_NAME: str = "ingestion-service"
    VERSION: str = "0.1.0"
    
    # SIEM Agent configuration (where events are sent)
    SIEM_AGENT_URL: str = os.getenv("SIEM_AGENT_URL", "http://siem_agent:8000")
    IAM_AGENT_URL: str = os.getenv("IAM_AGENT_URL", "http://iam_agent:8000")
    KEYCLOAK_CLIENT_ID: str = "sentinelgrid-web"
    IAM_TOKEN_VALIDATION_TIMEOUT: float = Field(default=5.0, gt=0, le=10, allow_inf_nan=False)
    IAM_VERIFIER_CA_BUNDLE: str | None = None
    IAM_USER_CLIENT_BINDINGS: tuple[UserClientBinding, ...] = Field(default=(), max_length=256)
    INGESTION_RUNTIME_READERS: tuple[RuntimeReader, ...] = Field(default=(), max_length=256)
    # OpenSearch configuration (direct ingest target)
    OPENSEARCH_URL: str = os.getenv("OPENSEARCH_URL", "http://opensearch:9200")
    OPENSEARCH_USERNAME: Optional[str] = os.getenv("OPENSEARCH_USERNAME")
    OPENSEARCH_PASSWORD: Optional[str] = os.getenv("OPENSEARCH_PASSWORD")

    # Embeddings/model-gateway for high-value ingest (pgvector)
    MODEL_GATEWAY_URL: str = os.getenv("MODEL_GATEWAY_URL", "http://model_gateway:8000")
    ENABLE_EMBEDDINGS: bool = os.getenv("ENABLE_EMBEDDINGS", "false").lower() in ("1", "true", "yes")
    EMBEDDINGS_MAX_PER_TENANT_PER_DAY: int = int(os.getenv("EMBEDDINGS_MAX_PER_TENANT_PER_DAY", "200"))
    
    # Batch processing configuration
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "500"))
    BATCH_TIMEOUT_SECONDS: int = int(os.getenv("BATCH_TIMEOUT_SECONDS", "10"))
    MAX_BATCH_SIZE: int = int(os.getenv("MAX_BATCH_SIZE", "1000"))
    
    # Rate limiting
    RATE_LIMIT_PER_TENANT: int = int(os.getenv("RATE_LIMIT_PER_TENANT", "10000"))  # events per minute
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    
    # Retry configuration
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_BACKOFF_SECONDS: float = float(os.getenv("RETRY_BACKOFF_SECONDS", "1.0"))
    
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

    def principal_settings(self) -> IngestionPrincipalSettings:
        return IngestionPrincipalSettings(_env_file=None, ENVIRONMENT=self.ENVIRONMENT,
            IAM_USER_CLIENT_BINDINGS=self.IAM_USER_CLIENT_BINDINGS, INGESTION_RUNTIME_READERS=self.INGESTION_RUNTIME_READERS)


settings = Settings()
