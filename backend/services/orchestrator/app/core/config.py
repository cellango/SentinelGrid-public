"""Configuration for Orchestrator Service."""

import os
from pydantic import model_validator
from pydantic_settings import SettingsConfigDict

from sg_core.service_security import (
    ServiceSecuritySettings,
    require_non_default_database_url,
)


class Settings(ServiceSecuritySettings):
    """Application settings."""

    REQUIRE_INTERNAL_TOKEN_IN_PROD = True
    REQUIRE_UPSTREAM_TLS_VERIFY_IN_PROD = True
    
    # Service info
    SERVICE_NAME: str = "orchestrator"
    VERSION: str = "0.1.0"
    
    # Service URLs
    SIEM_AGENT_URL: str = os.getenv("SIEM_AGENT_URL", "http://siem_agent:8000")
    IAM_AGENT_URL: str = os.getenv("IAM_AGENT_URL", "http://iam_agent:8000")
    MODEL_GATEWAY_URL: str = os.getenv("MODEL_GATEWAY_URL", "http://model_gateway:8000")
    DETECTION_SERVICE_URL: str = os.getenv("DETECTION_SERVICE_URL", "http://detection_service:8000")
    FRAMEWORK_SERVICE_URL: str = os.getenv("FRAMEWORK_SERVICE_URL", "http://framework_service:8000")
    EMAIL_INGESTION_SERVICE_URL: str = os.getenv("EMAIL_INGESTION_SERVICE_URL", "http://email_ingestion_service:8000")
    SOAR_AGENT_URL: str = os.getenv("SOAR_AGENT_URL", "http://soar_agent:8000")
    AUTOMATED_RESPONSE_SERVICE_URL: str = os.getenv("AUTOMATED_RESPONSE_SERVICE_URL", "http://automated_response_service:8000")
    COMPLIANCE_SERVICE_URL: str = os.getenv("COMPLIANCE_SERVICE_URL", "http://compliance_service:8000")
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"postgresql://{os.getenv('DB_USER', 'sg')}:{os.getenv('DB_PASSWORD', 'sg')}@{os.getenv('DB_HOST', 'postgres')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'sg')}"
    )
    
    # Timeouts
    SERVICE_TIMEOUT: int = int(os.getenv("SERVICE_TIMEOUT", "30"))
    
    # Snapshot configuration
    SNAPSHOT_ALERT_LIMIT: int = int(os.getenv("SNAPSHOT_ALERT_LIMIT", "10"))
    SNAPSHOT_EVENT_LOOKBACK_HOURS: int = int(os.getenv("SNAPSHOT_EVENT_LOOKBACK_HOURS", "24"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    @model_validator(mode="after")
    def _validate_security_posture(self):
        super()._validate_security_posture()
        require_non_default_database_url(self.ENVIRONMENT, self.DATABASE_URL, "DATABASE_URL")
        return self


settings = Settings()
