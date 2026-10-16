"""Configuration settings for Email Ingestion Service."""

import os
from typing import Optional

from sg_core.service_security import ServiceSecuritySettings


class Settings(ServiceSecuritySettings):
    """Application settings."""

    REQUIRE_INTERNAL_TOKEN_IN_PROD = True
    
    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "sg")
    DB_USER: str = os.getenv("DB_USER", "sg")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "sg")
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Email Provider Configuration
    EMAIL_PROVIDER: str = os.getenv("EMAIL_PROVIDER", "imap")  # imap, microsoft_graph, gmail
    
    # IMAP Configuration
    IMAP_HOST: Optional[str] = os.getenv("IMAP_HOST")
    IMAP_PORT: int = int(os.getenv("IMAP_PORT", "993"))
    IMAP_USER: Optional[str] = os.getenv("IMAP_USER")
    IMAP_PASSWORD: Optional[str] = os.getenv("IMAP_PASSWORD")
    IMAP_USE_SSL: bool = os.getenv("IMAP_USE_SSL", "true").lower() == "true"
    IMAP_MAILBOX: str = os.getenv("IMAP_MAILBOX", "INBOX")
    IMAP_POLL_INTERVAL_SECONDS: int = int(os.getenv("IMAP_POLL_INTERVAL_SECONDS", "300"))  # 5 minutes
    
    # Microsoft Graph API Configuration
    MS_GRAPH_CLIENT_ID: Optional[str] = os.getenv("MS_GRAPH_CLIENT_ID")
    MS_GRAPH_CLIENT_SECRET: Optional[str] = os.getenv("MS_GRAPH_CLIENT_SECRET")
    MS_GRAPH_TENANT_ID: Optional[str] = os.getenv("MS_GRAPH_TENANT_ID")
    MS_GRAPH_MAILBOX: str = os.getenv("MS_GRAPH_MAILBOX", "phishing@customer.sentinelgrid.com")
    
    # Google Gmail API Configuration
    GMAIL_CLIENT_ID: Optional[str] = os.getenv("GMAIL_CLIENT_ID")
    GMAIL_CLIENT_SECRET: Optional[str] = os.getenv("GMAIL_CLIENT_SECRET")
    GMAIL_REFRESH_TOKEN: Optional[str] = os.getenv("GMAIL_REFRESH_TOKEN")
    
    # Orchestrator URL (for triggering AI classification)
    ORCHESTRATOR_URL: str = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8000")
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "false").lower() == "true"
    
settings = Settings()
