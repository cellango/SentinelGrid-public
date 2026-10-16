"""Configuration for Audit Service."""

import os
from typing import Optional

from sg_core.service_security import ServiceSecuritySettings

class Settings(ServiceSecuritySettings):
    """Service settings."""
    
    # Service Info
    SERVICE_NAME: str = "audit-service"
    VERSION: str = "1.0.0"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL") or "postgresql://sentinelgrid:sentinelgrid@localhost:5432/sentinelgrid"
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "sentinelgrid")
    DB_USER: str = os.getenv("DB_USER", "sentinelgrid")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "sentinelgrid")

    def __post_init__(self):
        # If DATABASE_URL not explicitly set, build it from parts
        if not os.getenv("DATABASE_URL"):
            self.DATABASE_URL = f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Retention
    DEFAULT_HOT_RETENTION_DAYS: int = int(os.getenv("HOT_RETENTION_DAYS", "365"))
    DEFAULT_COLD_RETENTION_DAYS: int = int(os.getenv("COLD_RETENTION_DAYS", "1825"))
    DEFAULT_TOTAL_RETENTION_DAYS: int = int(os.getenv("TOTAL_RETENTION_DAYS", "2555"))
    
    # Archive Storage
    ARCHIVE_ENABLED: bool = os.getenv("ARCHIVE_ENABLED", "false").lower() == "true"
    ARCHIVE_BUCKET: Optional[str] = os.getenv("ARCHIVE_BUCKET")
    
    # AWS (for S3 archiving)
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")


settings = Settings()
settings.__post_init__()
