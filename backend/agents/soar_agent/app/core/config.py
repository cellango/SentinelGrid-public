"""Configuration for SOAR Agent Service."""

import os
from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sg_core.service_security import DEFAULT_INTERNAL_SERVICE_TOKEN

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
]
class Settings(BaseSettings):
    """Application settings."""

    ENVIRONMENT: str = "development"
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: DEFAULT_CORS_ORIGINS.copy())
    
    # Service info
    SERVICE_NAME: str = "soar-agent"
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
    
    # Redis (for caching)
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", "redis://redis:6379")
    
    # StackStorm SOAR configuration
    STACKSTORM_URL: Optional[str] = os.getenv("STACKSTORM_URL", "http://stackstorm:9101")
    STACKSTORM_API_KEY: Optional[str] = os.getenv("STACKSTORM_API_KEY")
    
    # Cortex enrichment configuration
    CORTEX_URL: Optional[str] = os.getenv("CORTEX_URL", "http://cortex:9001")
    CORTEX_API_KEY: Optional[str] = os.getenv("CORTEX_API_KEY")
    
    # n8n workflow engine configuration
    N8N_URL: Optional[str] = os.getenv("N8N_URL", "http://n8n:5678")
    N8N_API_KEY: Optional[str] = os.getenv("N8N_API_KEY")
    N8N_WEBHOOK_URL: Optional[str] = os.getenv("N8N_WEBHOOK_URL")
    
    # Ticketing integration (GLPI/Jira)
    GLPI_URL: Optional[str] = os.getenv("GLPI_URL")
    GLPI_API_TOKEN: Optional[str] = os.getenv("GLPI_API_TOKEN")
    
    JIRA_URL: Optional[str] = os.getenv("JIRA_URL")
    JIRA_USERNAME: Optional[str] = os.getenv("JIRA_USERNAME")
    JIRA_API_TOKEN: Optional[str] = os.getenv("JIRA_API_TOKEN")
    
    # Keycloak configuration (for tenant extraction)
    KEYCLOAK_URL: str = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
    KEYCLOAK_REALM: str = os.getenv("KEYCLOAK_REALM", "sentinelgrid")
    
    # Playbook execution
    PLAYBOOK_EXECUTION_TIMEOUT: int = int(os.getenv("PLAYBOOK_EXECUTION_TIMEOUT", "3600"))  # 1 hour default
    
    # Service URLs for containment playbook
    EMAIL_INGESTION_SERVICE_URL: Optional[str] = os.getenv("EMAIL_INGESTION_SERVICE_URL", "http://email_ingestion_service:8000")
    TICKETING_SERVICE_URL: Optional[str] = os.getenv("TICKETING_SERVICE_URL", "http://ticketing_service:8000")
    ACTION_AGENT_URL: Optional[str] = os.getenv("ACTION_AGENT_URL", "http://action_service:8000")
    IAM_AGENT_URL: Optional[str] = os.getenv("IAM_AGENT_URL", "http://iam_agent:8000")
    VULNERABILITY_SERVICE_URL: Optional[str] = os.getenv("VULNERABILITY_SERVICE_URL", "http://vulnerability_service:8000")
    CMDB_SERVICE_URL: Optional[str] = os.getenv("CMDB_SERVICE_URL", "http://cmdb_service:8000")
    FRAMEWORK_SERVICE_URL: Optional[str] = os.getenv("FRAMEWORK_SERVICE_URL", "http://framework_service:8000")
    MODEL_GATEWAY_URL: Optional[str] = os.getenv("MODEL_GATEWAY_URL", "http://model_gateway:8000")
    AGENT_RUNTIME_URL: Optional[str] = os.getenv("AGENT_RUNTIME_URL", "http://agent_runtime:8000")

    # Internal service authentication
    INTERNAL_SERVICE_TOKEN: str = DEFAULT_INTERNAL_SERVICE_TOKEN

    # Enrichment / integrations
    PARALLEL_ENRICHMENT: bool = os.getenv("PARALLEL_ENRICHMENT", "false").lower() == "true"
    THEHIVE_URL: Optional[str] = os.getenv("THEHIVE_URL")
    THEHIVE_API_KEY: Optional[str] = os.getenv("THEHIVE_API_KEY")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def _normalize_environment(cls, value):
        return str(value or "development").strip().lower()

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value):
        if value is None:
            return DEFAULT_CORS_ORIGINS.copy()
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _validate_security_posture(self):
        if self.ENVIRONMENT != "production":
            return self

        if not self.CORS_ORIGINS or any(origin == "*" for origin in self.CORS_ORIGINS):
            raise ValueError("CORS_ORIGINS must be an explicit allowlist in production")

        if self.INTERNAL_SERVICE_TOKEN == DEFAULT_INTERNAL_SERVICE_TOKEN:
            raise ValueError("INTERNAL_SERVICE_TOKEN cannot use the default value in production")

        return self


settings = Settings()
