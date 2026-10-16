"""Configuration for MCP Server."""

import os
from typing import Optional

from sg_core.service_security import ServiceSecuritySettings

class Settings(ServiceSecuritySettings):
    """Application settings."""

    REQUIRE_INTERNAL_TOKEN_IN_PROD = True
    
    # Service info
    SERVICE_NAME: str = "mcp-server"
    VERSION: str = "0.1.0"
    
    # Internal service URLs
    SIEM_AGENT_URL: str = os.getenv("SIEM_AGENT_URL", "http://siem_agent:8000")
    SOAR_AGENT_URL: str = os.getenv("SOAR_AGENT_URL", "http://soar_agent:8000")
    IAM_AGENT_URL: str = os.getenv("IAM_AGENT_URL", "http://iam_agent:8000")
    POSTURE_AGENT_URL: str = os.getenv("POSTURE_AGENT_URL", "http://posture_agent:8000")
    OBSERVABLES_SERVICE_URL: str = os.getenv("OBSERVABLES_SERVICE_URL", "http://observables_service:8000")
    DETECTION_SERVICE_URL: str = os.getenv("DETECTION_SERVICE_URL", "http://detection_service:8000")
    COMPLIANCE_SERVICE_URL: str = os.getenv("COMPLIANCE_SERVICE_URL", "http://compliance_service:8000")
    VULNERABILITY_SERVICE_URL: str = os.getenv("VULNERABILITY_SERVICE_URL", "http://vulnerability_service:8000")
    TICKETING_AGENT_URL: str = os.getenv("TICKETING_AGENT_URL", "http://ticketing_agent:8000")
    FRAMEWORK_SERVICE_URL: str = os.getenv("FRAMEWORK_SERVICE_URL", "http://framework_service:8000")
    
    # MCP settings
    MCP_AUDIT_ENABLED: bool = os.getenv("MCP_AUDIT_ENABLED", "true").lower() == "true"
    MCP_REQUIRE_APPROVAL_FOR_HIGH_RISK: bool = os.getenv("MCP_REQUIRE_APPROVAL_FOR_HIGH_RISK", "true").lower() == "true"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
