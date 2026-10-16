"""Configuration settings for Ticketing Agent Service."""

import os
from typing import Optional

from sg_core.service_security import ServiceSecuritySettings


class Settings(ServiceSecuritySettings):
    """Application settings."""

    REQUIRE_INTERNAL_TOKEN_IN_PROD = True
    REQUIRE_UPSTREAM_TLS_VERIFY_IN_PROD = True
    
    SERVICE_NAME: str = "ticketing-agent"
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
    THEHIVE_URL: str = os.getenv("THEHIVE_URL", "http://thehive:9000")
    THEHIVE_API_KEY: Optional[str] = os.getenv("THEHIVE_API_KEY")
    SOAR_AGENT_URL: str = os.getenv("SOAR_AGENT_URL", "http://soar_agent:8000")
    AI_ENRICHMENT_AGENT_URL: str = os.getenv("AI_ENRICHMENT_AGENT_URL", SOAR_AGENT_URL)
    FRAMEWORK_SERVICE_URL: str = os.getenv("FRAMEWORK_SERVICE_URL", "http://framework_service:8000")
    VULNERABILITY_SERVICE_URL: str = os.getenv("VULNERABILITY_SERVICE_URL", "http://vulnerability_service:8000")
    SCANNER_ORCHESTRATOR_URL: str = os.getenv("SCANNER_ORCHESTRATOR_URL", "http://scanner_orchestrator:8000")
    MODEL_GATEWAY_URL: str = os.getenv("MODEL_GATEWAY_URL", "http://model_gateway:8000")
    AGENT_RUNTIME_URL: str = os.getenv("AGENT_RUNTIME_URL", "http://agent_runtime:8000")
    
    # Zammad (SaaS-managed) integration
    TICKETING_PROVIDER: str = os.getenv("TICKETING_PROVIDER", "zammad")  # zammad | thehive
    ZAMMAD_URL: str = os.getenv("ZAMMAD_URL", "http://zammad:3000")
    ZAMMAD_TOKEN: Optional[str] = os.getenv("ZAMMAD_TOKEN")
    ZAMMAD_GROUP: str = os.getenv("ZAMMAD_GROUP", "Users")
    ZAMMAD_PRIORITY_MAP: str = os.getenv("ZAMMAD_PRIORITY_MAP", "low:1,medium:2,high:3,critical:4")
    ZAMMAD_SLA_MINUTES_DEFAULT: int = int(os.getenv("ZAMMAD_SLA_MINUTES_DEFAULT", "240"))
    
settings = Settings()
