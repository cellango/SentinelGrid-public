"""Configuration for Detection Service."""

import os
from pydantic import Field, model_validator
from sg_core.iam_verification import IAMVerificationSettings
from sg_core.user_principals import UserClientBinding
from app.core.principal_policy import DetectionPrincipalSettings, RuntimeReader

from sg_core.service_security import ServiceSecuritySettings


class Settings(ServiceSecuritySettings):
    """Application settings."""

    REQUIRE_INTERNAL_TOKEN_IN_PROD = True
    
    # Service info
    SERVICE_NAME: str = "detection-service"
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
    DETECTION_SCHEDULER_READERS: tuple[RuntimeReader, ...] = Field(default=(), max_length=256)

    # SIEM Agent configuration
    SIEM_AGENT_URL: str = os.getenv("SIEM_AGENT_URL", "http://siem_agent:8000")
    # Service URLs for incident creation
    TICKETING_SERVICE_URL: str = os.getenv("TICKETING_SERVICE_URL", "http://ticketing_service:8000")
    FRAMEWORK_SERVICE_URL: str = os.getenv("FRAMEWORK_SERVICE_URL", "http://framework_service:8000")
    AGENT_RUNTIME_URL: str = os.getenv("AGENT_RUNTIME_URL", "http://agent_runtime:8000")
    
    # Auto-create incidents for high-severity alerts
    AUTO_CREATE_INCIDENTS: bool = os.getenv("AUTO_CREATE_INCIDENTS", "true").lower() == "true"
    
    # Rule evaluation configuration
    EVALUATION_BATCH_SIZE: int = int(os.getenv("EVALUATION_BATCH_SIZE", "1000"))
    EVALUATION_INTERVAL_SECONDS: int = int(os.getenv("EVALUATION_INTERVAL_SECONDS", "60"))
    
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

    def principal_settings(self) -> DetectionPrincipalSettings:
        return DetectionPrincipalSettings(_env_file=None, ENVIRONMENT=self.ENVIRONMENT,
            IAM_USER_CLIENT_BINDINGS=self.IAM_USER_CLIENT_BINDINGS, DETECTION_SCHEDULER_READERS=self.DETECTION_SCHEDULER_READERS)


settings = Settings()
