"""Configuration settings for Framework Mapping Service."""

import os
from typing import Optional

from sg_core.service_security import ServiceSecuritySettings


class Settings(ServiceSecuritySettings):
    """Application settings."""

    REQUIRE_INTERNAL_TOKEN_IN_PROD = True
    
    SERVICE_NAME: str = "framework-service"
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
    
    # Model Gateway (for AI-assisted mapping)
    MODEL_GATEWAY_URL: str = os.getenv("MODEL_GATEWAY_URL", "http://model_gateway:8000")
    # Knowledge Base
    KNOWLEDGE_BASE_PATH: Optional[str] = os.getenv("KNOWLEDGE_BASE_PATH")
    
settings = Settings()
