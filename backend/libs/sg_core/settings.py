"""Shared settings and configuration."""

import os
from typing import Optional

class Settings:
    """Application settings."""
    
    # Database
    DB_URL: str = os.getenv("DB_URL", "postgresql://sg:sg@localhost:5432/sg")
    
    # Keycloak
    KEYCLOAK_URL: str = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
    KEYCLOAK_REALM: str = os.getenv("KEYCLOAK_REALM", "sentinelgrid")
    KEYCLOAK_CLIENT_ID: str = os.getenv("KEYCLOAK_CLIENT_ID", "sentinelgrid-web")
    
    # Service URLs
    ORCHESTRATOR_URL: str = os.getenv("ORCHESTRATOR_URL", "http://localhost:8001")
    MODEL_GATEWAY_URL: str = os.getenv("MODEL_GATEWAY_URL", "http://localhost:8002")
    SIEM_AGENT_URL: str = os.getenv("SIEM_AGENT_URL", "http://localhost:8003")
    SOAR_AGENT_URL: str = os.getenv("SOAR_AGENT_URL", "http://localhost:8004")
    IAM_AGENT_URL: str = os.getenv("IAM_AGENT_URL", "http://localhost:8005")
    POSTURE_AGENT_URL: str = os.getenv("POSTURE_AGENT_URL", "http://localhost:8006")
    
    # LLM
    MODEL_SERVER_URL: str = os.getenv("MODEL_SERVER_URL", "http://localhost:8007")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "secgpt-base")
    MODEL_VERSION: str = os.getenv("MODEL_VERSION", "1.0.0")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")


settings = Settings()

