"""Configuration for Compliance Service."""

import os
from pydantic_settings import SettingsConfigDict
from typing import Optional

from sg_core.service_security import ServiceSecuritySettings


def _env_flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


class Settings(ServiceSecuritySettings):
    """Application settings."""

    REQUIRE_INTERNAL_TOKEN_IN_PROD = True
    
    # Service info
    SERVICE_NAME: str = "compliance-service"
    VERSION: str = "0.1.0"
    
    # Database configuration (uses main PostgreSQL database)
    DB_HOST: str = os.getenv("DB_HOST", "postgres")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "sg")
    DB_USER: str = os.getenv("DB_USER", "sg")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "sg")
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL from components."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Service URLs
    SOAR_AGENT_URL: str = os.getenv("SOAR_AGENT_URL", "http://soar_agent:8000")
    FRAMEWORK_SERVICE_URL: str = os.getenv("FRAMEWORK_SERVICE_URL", "http://framework_service:8000")
    AGENT_RUNTIME_URL: str = os.getenv("AGENT_RUNTIME_URL", "http://agent_runtime:8000")
    COMPLIANCE_AGENT_TRIGGER_TIMEOUT_SECONDS: float = float(
        os.getenv("COMPLIANCE_AGENT_TRIGGER_TIMEOUT_SECONDS", "5.0")
    )
    
    # Remediation settings
    AUTO_REMEDIATE_ENABLED: bool = os.getenv("AUTO_REMEDIATE_ENABLED", "false").lower() == "true"
    REMEDIATION_TIMEOUT: int = int(os.getenv("REMEDIATION_TIMEOUT", "3600"))  # 1 hour default

    # Compliance rollout flags. These default off because the current runtime is
    # SOC 2 readiness/reporting; later phases enable the generalized surfaces.
    COMPLIANCE_MULTI_FRAMEWORK_ENABLED: bool = _env_flag("COMPLIANCE_MULTI_FRAMEWORK_ENABLED")
    COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED: bool = _env_flag("COMPLIANCE_EVIDENCE_REPOSITORY_ENABLED")
    COMPLIANCE_AGENT_ENABLED: bool = _env_flag("COMPLIANCE_AGENT_ENABLED")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
