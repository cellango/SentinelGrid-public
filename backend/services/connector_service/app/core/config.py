"""Configuration for Connector Service."""

import os
from typing import Optional

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
    
settings = Settings()
