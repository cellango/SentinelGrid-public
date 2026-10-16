"""Configuration for SIEM Agent Service."""

import os
from typing import Optional

from pydantic import model_validator

from sg_core.service_security import (
    DEFAULT_OPENSEARCH_HOSTS,
    ServiceSecuritySettings,
    require_authenticated_redis_url,
    require_non_default_database_url,
    require_secure_service_url,
    require_tls_verification,
)


class Settings(ServiceSecuritySettings):
    """Application settings."""

    REQUIRE_INTERNAL_TOKEN_IN_PROD = True
    REQUIRE_UPSTREAM_TLS_VERIFY_IN_PROD = True
    
    # Service info
    SERVICE_NAME: str = "siem-agent"
    VERSION: str = "0.1.0"
    
    # OpenSearch configuration
    OPENSEARCH_URL: str = os.getenv("OPENSEARCH_URL", "http://opensearch:9200")
    OPENSEARCH_USER: Optional[str] = os.getenv("OPENSEARCH_USER")
    OPENSEARCH_PASSWORD: Optional[str] = os.getenv("OPENSEARCH_PASSWORD")
    OPENSEARCH_USE_SSL: bool = os.getenv("OPENSEARCH_USE_SSL", "false").lower() == "true"
    OPENSEARCH_VERIFY_CERTS: bool = os.getenv("OPENSEARCH_VERIFY_CERTS", "false").lower() == "true"
    OPENSEARCH_TIMEOUT: int = int(os.getenv("OPENSEARCH_TIMEOUT", "30"))
    OPENSEARCH_MAX_RETRIES: int = int(os.getenv("OPENSEARCH_MAX_RETRIES", "3"))
    
    # Database configuration (for metadata)
    DB_HOST: str = os.getenv("DB_HOST", "postgres")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "sg")
    DB_USER: str = os.getenv("DB_USER", "sg")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "sg")
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL from components."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Redis configuration (for caching)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379")
    
    # Index configuration
    INDEX_RETENTION_DAYS: int = int(os.getenv("INDEX_RETENTION_DAYS", "30"))
    INDEX_SHARDS: int = int(os.getenv("INDEX_SHARDS", "1"))
    INDEX_REPLICAS: int = int(os.getenv("INDEX_REPLICAS", "0"))
    
    # Keycloak configuration (for tenant extraction)
    KEYCLOAK_URL: str = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
    KEYCLOAK_REALM: str = os.getenv("KEYCLOAK_REALM", "sentinelgrid")
    IAM_AGENT_URL: str = os.getenv("IAM_AGENT_URL", "http://iam_agent:8000")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"
    
    # System (platform) tenant id used for built-in detections/playbooks
    SYSTEM_TENANT_ID: str = os.getenv("SYSTEM_TENANT_ID", "9c7df7a9-5a0b-4412-a41c-0c0ea777b2f0")

    # SentinelGuard ingest service
    INGEST_URL: str = os.getenv("INGEST_URL", "http://sentinelguard-server:8085/ingest")
    INGEST_TOKEN: Optional[str] = os.getenv("INGEST_TOKEN")

    # Router URL (for shared monitor forwarding)
    ROUTER_URL: str = os.getenv(
        "ROUTER_URL",
        "http://siem_agent:8000/api/v1/router/opensearch-webhook",
    )
    
    # Index retention (days)
    INDEX_RETENTION_DAYS: int = int(os.getenv("INDEX_RETENTION_DAYS", "90"))
    
    # Redis (for caching)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    @model_validator(mode="after")
    def _validate_security_posture(self):
        super()._validate_security_posture()

        require_tls_verification(self.ENVIRONMENT, self.OPENSEARCH_VERIFY_CERTS, "OPENSEARCH_VERIFY_CERTS")
        require_tls_verification(self.ENVIRONMENT, self.OPENSEARCH_USE_SSL, "OPENSEARCH_USE_SSL")
        require_non_default_database_url(self.ENVIRONMENT, self.DATABASE_URL, "DATABASE_URL")
        require_authenticated_redis_url(self.ENVIRONMENT, self.REDIS_URL, "REDIS_URL")
        require_secure_service_url(
            self.ENVIRONMENT,
            self.OPENSEARCH_URL,
            "OPENSEARCH_URL",
            disallowed_hosts=DEFAULT_OPENSEARCH_HOSTS,
        )
        return self


settings = Settings()
