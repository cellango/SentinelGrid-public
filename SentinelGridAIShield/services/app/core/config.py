import os
from typing import Optional

DEFAULT_INTERNAL_SERVICE_TOKEN = "internal-service-token-change-in-production"


class Settings:
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development").strip().lower()
    # Database
    DB_URL: str = os.getenv("DB_URL", "postgresql://sg:sg@localhost:5432/sg")
    
    # OpenSearch
    OPENSEARCH_URL: str = os.getenv("OPENSEARCH_URL", "http://localhost:9200")
    OPENSEARCH_USE_SSL: bool = os.getenv("OPENSEARCH_USE_SSL", "false").lower() == "true"
    
    # IAM Agent
    IAM_AGENT_URL: str = os.getenv("IAM_AGENT_URL", "http://localhost:8000")
    
    # Model Gateway
    MODEL_GATEWAY_URL: str = os.getenv("MODEL_GATEWAY_URL", "http://localhost:8002")
    
    # Internal service token
    INTERNAL_SERVICE_TOKEN: str = os.getenv("INTERNAL_SERVICE_TOKEN", DEFAULT_INTERNAL_SERVICE_TOKEN)
    SKIP_DB_INIT_ON_STARTUP: bool = os.getenv("AI_SHIELD_SKIP_DB_INIT_ON_STARTUP", "false").lower() == "true"

    # External SIEM export interface
    SIEM_EXPORT_ENABLED: bool = os.getenv("SIEM_EXPORT_ENABLED", "false").lower() == "true"
    SIEM_EXPORT_CONFIG_FILE: str = os.getenv("SIEM_EXPORT_CONFIG_FILE", "/app/config/siem-destinations.yaml")
    SIEM_EXPORT_BATCH_SIZE: int = int(os.getenv("SIEM_EXPORT_BATCH_SIZE", "100"))
    SIEM_EXPORT_TIMEOUT_SECONDS: int = int(os.getenv("SIEM_EXPORT_TIMEOUT_SECONDS", "10"))
    SIEM_EXPORT_RETRY_MAX: int = int(os.getenv("SIEM_EXPORT_RETRY_MAX", "3"))

    # Optional platform integration for sending risky AI telemetry into the main SentinelGrid workflow.
    PLATFORM_ALERT_INGEST_ENABLED: bool = os.getenv("PLATFORM_ALERT_INGEST_ENABLED", "false").lower() == "true"
    PLATFORM_API_URL: str = os.getenv("PLATFORM_API_URL", "http://api_gateway:8000")
    PLATFORM_ALERT_INGEST_PATH: str = os.getenv(
        "PLATFORM_ALERT_INGEST_PATH",
        "/api/v1/internal/ai-shield/events",
    )
    PLATFORM_ALERT_INGEST_TIMEOUT_SECONDS: int = int(
        os.getenv("PLATFORM_ALERT_INGEST_TIMEOUT_SECONDS", "10")
    )
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("AI_SHIELD_CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]

    def validate_security_posture(self) -> None:
        if self.ENVIRONMENT != "production":
            return
        if self.INTERNAL_SERVICE_TOKEN == DEFAULT_INTERNAL_SERVICE_TOKEN:
            raise RuntimeError("INTERNAL_SERVICE_TOKEN cannot use the default value in production")

settings = Settings()
settings.validate_security_posture()
