"""Configuration for Automated Response Service."""

import os
from typing import Optional

from sg_core.service_security import ServiceSecuritySettings


class Settings(ServiceSecuritySettings):
    """Application settings."""

    REQUIRE_INTERNAL_TOKEN_IN_PROD = True
    
    # Service info
    SERVICE_NAME: str = "automated-response-service"
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
    DETECTION_SERVICE_URL: str = os.getenv("DETECTION_SERVICE_URL", "http://detection_service:8000")
    
    # Internal service token for service-to-service communication
    # Trigger evaluation settings
    MAX_TRIGGER_EVALUATION_TIME: int = int(os.getenv("MAX_TRIGGER_EVALUATION_TIME", "30"))  # seconds
    ENABLE_AUTO_TRIGGER: bool = os.getenv("ENABLE_AUTO_TRIGGER", "true").lower() == "true"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
settings = Settings()
