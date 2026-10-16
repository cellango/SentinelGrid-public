"""Configuration for Wazuh Manager Service."""

import os
from typing import Optional

from sg_core.service_security import ServiceSecuritySettings


class Settings(ServiceSecuritySettings):
    """Application settings."""

    REQUIRE_INTERNAL_TOKEN_IN_PROD = True
    REQUIRE_UPSTREAM_TLS_VERIFY_IN_PROD = True
    
    # Service info
    SERVICE_NAME: str = "wazuh-manager-service"
    VERSION: str = "1.0.0"
    
    # Database configuration
    DB_URL: str = os.getenv("DB_URL", "postgresql://sg:sg@postgres:5432/sg")
    
    # Wazuh Manager API configuration
    WAZUH_MANAGER_URL: str = os.getenv("WAZUH_MANAGER_URL", "http://wazuh-manager:55000")
    WAZUH_API_USERNAME: str = os.getenv("WAZUH_API_USERNAME", "wazuh-api")
    WAZUH_API_PASSWORD: str = os.getenv("WAZUH_API_PASSWORD", "MyS3cr3tP455w0rd!")
    
    # IAM Agent (for token validation)
    IAM_AGENT_URL: str = os.getenv("IAM_AGENT_URL", "http://iam_agent:8000")
    
    # Keycloak configuration (for direct validation if needed)
    KEYCLOAK_URL: str = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
    KEYCLOAK_REALM: str = os.getenv("KEYCLOAK_REALM", "sentinelgrid")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
settings = Settings()
