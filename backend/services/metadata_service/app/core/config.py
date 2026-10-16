"""Configuration for metadata service."""

import os

from sg_core.service_security import ServiceSecuritySettings


class Settings(ServiceSecuritySettings):
    """Service configuration."""
    
    SERVICE_NAME: str = "metadata-service"
    VERSION: str = "1.0.0"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Database
    DB_URL: str = os.getenv("DB_URL", "postgresql://sg:sg@localhost:5432/sg")
    
    # Service URLs
    IAM_AGENT_URL: str = os.getenv("IAM_AGENT_URL", "http://iam_agent:8000")
    
settings = Settings()
