"""Configuration settings for Action Agent Service."""

import os
from typing import Optional

from sg_core.service_security import ServiceSecuritySettings


class Settings(ServiceSecuritySettings):
    """Application settings."""

    REQUIRE_INTERNAL_TOKEN_IN_PROD = True
    
    SERVICE_NAME: str = "action-agent"
    VERSION: str = "0.1.0"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Database
    DB_HOST: str = os.getenv("DB_HOST", "postgres")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "sg")
    DB_USER: str = os.getenv("DB_USER", "sg")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "sg")
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Service URLs
    IAM_AGENT_URL: str = os.getenv("IAM_AGENT_URL", "http://iam_agent:8000")
    TICKETING_SERVICE_URL: str = os.getenv("TICKETING_SERVICE_URL", "http://ticketing_agent:8000")
    
    # Action Settings
    REQUIRE_APPROVAL: bool = os.getenv("REQUIRE_APPROVAL", "true").lower() == "true"
    ACTION_TIMEOUT_SECONDS: int = int(os.getenv("ACTION_TIMEOUT_SECONDS", "300"))
    
settings = Settings()
