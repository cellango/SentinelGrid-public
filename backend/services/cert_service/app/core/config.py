"""Configuration for Certificate Service."""

import os
from typing import Optional

from sg_core.service_security import ServiceSecuritySettings


class Settings(ServiceSecuritySettings):
    """Application settings."""

    REQUIRE_INTERNAL_TOKEN_IN_PROD = True
    
    # Service info
    SERVICE_NAME: str = "cert-service"
    VERSION: str = "0.1.0"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"postgresql://{os.getenv('DB_USER', 'sg')}:{os.getenv('DB_PASSWORD', 'sg')}@{os.getenv('DB_HOST', 'postgres')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'sg')}"
    )
    
    # CA Backend Configuration
    CA_BACKEND_TYPE: str = os.getenv("CA_BACKEND_TYPE", "ejbca")  # 'ejbca', 'step-ca', or 'aws-acm-pca'
    
    # EJBCA Configuration
    EJBCA_URL: str = os.getenv("EJBCA_URL", "https://ejbca:8443")
    EJBCA_USERNAME: str = os.getenv("EJBCA_USERNAME", "admin")
    EJBCA_PASSWORD: str = os.getenv("EJBCA_PASSWORD", "admin")
    EJBCA_CA_NAME: str = os.getenv("EJBCA_CA_NAME", "SentinelGrid-Issuing-CA")
    EJBCA_CERTIFICATE_PROFILE: str = os.getenv("EJBCA_CERTIFICATE_PROFILE", "service-tls")
    EJBCA_VERIFY_SSL: bool = os.getenv("EJBCA_VERIFY_SSL", "False").lower() == "true"
    
    # Enrollment Protocol Configuration
    EJBCA_ACME_ALIAS: Optional[str] = os.getenv("EJBCA_ACME_ALIAS")  # Optional per-tenant ACME alias
    EJBCA_SCEP_RA_NAME: Optional[str] = os.getenv("EJBCA_SCEP_RA_NAME")  # Optional SCEP RA name
    EJBCA_EST_ALIAS: Optional[str] = os.getenv("EJBCA_EST_ALIAS")  # Optional EST alias
    
    # Step-CA Configuration
    STEP_CA_URL: str = os.getenv("STEP_CA_URL", "http://step-ca:9000")
    STEP_CA_PROVISIONER_NAME: str = os.getenv("STEP_CA_PROVISIONER_NAME", "sentinelgrid")
    STEP_CA_PROVISIONER_PASSWORD: Optional[str] = os.getenv("STEP_CA_PROVISIONER_PASSWORD")
    STEP_CA_ROOT_CA_PATH: Optional[str] = os.getenv("STEP_CA_ROOT_CA_PATH", "/etc/step-ca/root_ca.crt")
    
    # AWS ACM Private CA Configuration (optional)
    AWS_ACM_PCA_ARN: Optional[str] = os.getenv("AWS_ACM_PCA_ARN")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    
    # Certificate defaults
    DEFAULT_CERT_TTL_HOURS: int = int(os.getenv("DEFAULT_CERT_TTL_HOURS", "720"))  # 30 days
    SERVICE_CERT_TTL_HOURS: int = int(os.getenv("SERVICE_CERT_TTL_HOURS", "2160"))  # 90 days
    AGENT_CERT_TTL_HOURS: int = int(os.getenv("AGENT_CERT_TTL_HOURS", "720"))  # 30 days
    RENEWAL_THRESHOLD_DAYS: int = int(os.getenv("RENEWAL_THRESHOLD_DAYS", "7"))  # Renew 7 days before expiry
    
    # Security
    BOOTSTRAP_TOKEN_LENGTH: int = int(os.getenv("BOOTSTRAP_TOKEN_LENGTH", "32"))
    BOOTSTRAP_TOKEN_TTL_HOURS: int = int(os.getenv("BOOTSTRAP_TOKEN_TTL_HOURS", "24"))
    
    # Keycloak (for service authentication)
    KEYCLOAK_URL: str = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
    KEYCLOAK_REALM: str = os.getenv("KEYCLOAK_REALM", "sentinelgrid")
    
    # IAM Agent (for token validation)
    IAM_AGENT_URL: str = os.getenv("IAM_AGENT_URL", "http://iam_agent:8000")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"
    
settings = Settings()
