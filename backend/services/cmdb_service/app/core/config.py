"""Configuration settings for CMDB Service."""

import os
from typing import Optional

from sg_core.service_security import ServiceSecuritySettings


class Settings(ServiceSecuritySettings):
    """Application settings."""
    
    SERVICE_NAME: str = "cmdb-service"
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
    
    # CloudQuery Integration (for cloud asset discovery)
    CLOUDQUERY_ENABLED: bool = os.getenv("CLOUDQUERY_ENABLED", "false").lower() == "true"
    CLOUDQUERY_DB_URL: Optional[str] = os.getenv("CLOUDQUERY_DB_URL")
    
    # Asset Sync
    ASSET_SYNC_INTERVAL_HOURS: int = int(os.getenv("ASSET_SYNC_INTERVAL_HOURS", "24"))
    
settings = Settings()
