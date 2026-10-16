"""Configuration settings for Reporting Service."""

import os
from pydantic_settings import SettingsConfigDict

from sg_core.service_security import ServiceSecuritySettings


class Settings(ServiceSecuritySettings):
    """Application settings."""

    REQUIRE_INTERNAL_TOKEN_IN_PROD = True
    
    # Service info
    SERVICE_NAME: str = "reporting-service"
    VERSION: str = "0.1.0"
    
    # Database
    DB_URL: str = os.getenv("DB_URL", "postgresql://sg:sg@postgres:5432/sg")
    
    # Storage (for generated reports)
    REPORT_STORAGE_PATH: str = os.getenv("REPORT_STORAGE_PATH", "/tmp/reports")
    REPORT_STORAGE_URL: str = os.getenv("REPORT_STORAGE_URL", "http://localhost:8010/reports")
    
    # Report generation
    REPORT_RETENTION_DAYS: int = int(os.getenv("REPORT_RETENTION_DAYS", "90"))
    MAX_REPORT_SIZE_MB: int = int(os.getenv("MAX_REPORT_SIZE_MB", "50"))
    
    # External service URLs
    ORCHESTRATOR_URL: str = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8000")
    SIEM_AGENT_URL: str = os.getenv("SIEM_AGENT_URL", "http://siem_agent:8000")
    IAM_AGENT_URL: str = os.getenv("IAM_AGENT_URL", "http://iam_agent:8000")
    COMPLIANCE_SERVICE_URL: str = os.getenv("COMPLIANCE_SERVICE_URL", "http://compliance_service:8000")
    AUDIT_SERVICE_URL: str = os.getenv("AUDIT_SERVICE_URL", "http://audit_service:8000")
    AGENT_RUNTIME_URL: str = os.getenv("AGENT_RUNTIME_URL", "http://agent_runtime:8000")
    COMPLIANCE_AGENT_ENABLED: bool = os.getenv("COMPLIANCE_AGENT_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    COMPLIANCE_AGENT_TRIGGER_TIMEOUT_SECONDS: float = float(
        os.getenv("COMPLIANCE_AGENT_TRIGGER_TIMEOUT_SECONDS", "5.0")
    )
    
    # Email configuration (for scheduled reports)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "localhost")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "reports@sentinelgrid.com")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
