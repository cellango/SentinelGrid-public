"""Configuration for IAM Agent Service."""

import os
from dataclasses import dataclass
from typing import Optional, Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sg_core.service_security import (
    DEFAULT_INTERNAL_SERVICE_TOKEN,
    DEFAULT_KEYCLOAK_HOSTS,
    DEFAULT_VAULT_HOSTS,
    normalize_environment,
    parse_cors_origins,
    require_authenticated_redis_url,
    require_explicit_cors_allowlist,
    require_https_public_origins,
    require_non_default_database_url,
    require_non_default_internal_token,
    require_secure_service_url,
    require_tls_verification,
)

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
]
DEFAULT_KEYCLOAK_ADMIN_USER = "admin"
DEFAULT_KEYCLOAK_ADMIN_PASSWORD = "admin"
DEFAULT_KEYCLOAK_ADMIN_CLIENT_ID = "sentinelgrid-iam-agent"


class KeycloakAdminAuthConfigError(RuntimeError):
    """Raised when the runtime Keycloak admin auth configuration is unsafe or incomplete."""


@dataclass(frozen=True)
class KeycloakAdminRuntimeAuth:
    """Resolved Keycloak admin auth mode for runtime clients."""

    mode: Literal["service_account", "password"]
    user_realm_name: str
    token_payload: dict[str, str]
    python_keycloak_kwargs: dict[str, str]

class Settings(BaseSettings):
    """Application settings."""
    
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: DEFAULT_CORS_ORIGINS.copy())

    # Service info
    SERVICE_NAME: str = "iam-agent"
    VERSION: str = "0.1.0"
    
    # Keycloak configuration
    KEYCLOAK_URL: str = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
    KEYCLOAK_REALM: str = os.getenv("KEYCLOAK_REALM", "sentinelgrid")
    # Explicit public issuer bases when browser and internal Keycloak origins differ.
    KEYCLOAK_ISSUER_BASE_URLS: list[str] = Field(default_factory=list)
    
    # Alerting / Slack
    SLACK_WEBHOOK_URL: Optional[str] = os.getenv("SLACK_WEBHOOK_URL")
    KEYCLOAK_CLIENT_ID: str = os.getenv("KEYCLOAK_CLIENT_ID", "sentinelgrid-iam-agent")
    KEYCLOAK_CLIENT_SECRET: Optional[str] = os.getenv("KEYCLOAK_CLIENT_SECRET")
    
    # Keycloak admin credentials (for service account)
    KEYCLOAK_ADMIN_USER: str = DEFAULT_KEYCLOAK_ADMIN_USER
    KEYCLOAK_ADMIN_PASSWORD: str = DEFAULT_KEYCLOAK_ADMIN_PASSWORD
    KEYCLOAK_ADMIN_TOKEN_REALM: str = os.getenv("KEYCLOAK_ADMIN_TOKEN_REALM", "master")
    KEYCLOAK_ADMIN_CLIENT_ID: str = os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", DEFAULT_KEYCLOAK_ADMIN_CLIENT_ID)
    KEYCLOAK_ADMIN_CLIENT_SECRET: Optional[str] = os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET") or os.getenv("KEYCLOAK_CLIENT_SECRET")
    KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT: bool = os.getenv("KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT", "false").lower() == "true"
    
    # Database (for identity cache)
    DB_URL: Optional[str] = os.getenv("DB_URL")
    IAM_ENABLE_SERVICE_ACCOUNTS: bool = False  # IAM-local registry only; no provider/auth integration.
    IAM_ROLE_SYNC_REALMS: dict[str, str] = Field(default_factory=dict)
    IAM_DB_URL: Optional[str] = None  # Separate access-grant store; never inferred from DB_URL.
    
    # Redis (for caching JWKS)
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", "redis://redis:6379")
    
    # JWKS caching
    JWKS_CACHE_TTL: int = int(os.getenv("JWKS_CACHE_TTL", "3600"))  # 1 hour
    
    # Token validation
    TOKEN_VALIDATION_TIMEOUT: int = int(os.getenv("TOKEN_VALIDATION_TIMEOUT", "5"))

    # Vault configuration
    VAULT_ADDR: str = os.getenv("VAULT_ADDR", "http://vault:8200")
    VAULT_TOKEN: Optional[str] = os.getenv("VAULT_TOKEN")
    VAULT_NAMESPACE: Optional[str] = os.getenv("VAULT_NAMESPACE")
    VAULT_MOUNT: str = os.getenv("VAULT_MOUNT", "secret")
    VAULT_VERIFY_TLS: bool = os.getenv("VAULT_VERIFY_TLS", "false").lower() == "true"
    UPSTREAM_TLS_VERIFY: bool = os.getenv("UPSTREAM_TLS_VERIFY", "false").lower() == "true"
    
    # AI/LLM Configuration
    MODEL_GATEWAY_URL: str = os.getenv("MODEL_GATEWAY_URL", "http://model_gateway:8000")
    
    # Model Provider Configuration (enables easy model swapping)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "model_gateway")  # 'model_gateway', 'llama_cpp', 'openai_compatible'
    LLM_FALLBACK_PROVIDER: Optional[str] = os.getenv("LLM_FALLBACK_PROVIDER")  # Optional fallback
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "qwen2.5-coder-7b")
    LLM_TEMPERATURE: str = os.getenv("LLM_TEMPERATURE", "0.3")
    LLM_MAX_TOKENS: str = os.getenv("LLM_MAX_TOKENS", "500")
    
    # llama.cpp Configuration (if using direct llama.cpp)
    LLAMA_CPP_MODEL_PATH: Optional[str] = os.getenv("LLAMA_CPP_MODEL_PATH")
    LLAMA_CPP_THREADS: str = os.getenv("LLAMA_CPP_THREADS", "4")
    
    # OpenAI-Compatible API (optional fallback)
    OPENAI_COMPATIBLE_URL: Optional[str] = os.getenv("OPENAI_COMPATIBLE_URL")
    OPENAI_COMPATIBLE_API_KEY: Optional[str] = os.getenv("OPENAI_COMPATIBLE_API_KEY")
    OPENAI_COMPATIBLE_MODEL: str = os.getenv("OPENAI_COMPATIBLE_MODEL", "gpt-3.5-turbo")
    
    # Embeddings Configuration
    EMBEDDINGS_MODEL: str = os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    
    # Workflow Integration Configuration
    SOAR_SERVICE_URL: str = os.getenv("SOAR_SERVICE_URL", "http://soar_agent:8000")
    WORKFLOW_ENGINE_URL: str = os.getenv("WORKFLOW_ENGINE_URL", "http://workflow_engine:8000")
    COMPLIANCE_SERVICE_URL: str = os.getenv("COMPLIANCE_SERVICE_URL", "http://compliance_service:8000")
    
    # Cert Service Configuration
    CERT_SERVICE_URL: str = os.getenv("CERT_SERVICE_URL", "http://cert_service:8000")
    INTERNAL_SERVICE_TOKEN: str = DEFAULT_INTERNAL_SERVICE_TOKEN
    
    # Security Configuration
    ENABLE_RATE_LIMITING: bool = os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"
    RATE_LIMIT_ENABLED: bool = ENABLE_RATE_LIMITING  # Alias for clarity
    
    # Stripe Payment Configuration
    STRIPE_SECRET_KEY: Optional[str] = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY: Optional[str] = os.getenv("STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET: Optional[str] = os.getenv("STRIPE_WEBHOOK_SECRET")
    STRIPE_PRICE_ID_MONTHLY_STARTER: Optional[str] = os.getenv("STRIPE_PRICE_ID_MONTHLY_STARTER")
    STRIPE_PRICE_ID_YEARLY_STARTER: Optional[str] = os.getenv("STRIPE_PRICE_ID_YEARLY_STARTER")
    STRIPE_PRICE_ID_MONTHLY_PROFESSIONAL: Optional[str] = os.getenv("STRIPE_PRICE_ID_MONTHLY_PROFESSIONAL")
    STRIPE_PRICE_ID_YEARLY_PROFESSIONAL: Optional[str] = os.getenv("STRIPE_PRICE_ID_YEARLY_PROFESSIONAL")
    
    # Development mode - bypass Stripe for testing
    PAYMENT_DEV_MODE: bool = os.getenv("PAYMENT_DEV_MODE", "false").lower() == "true"

    # Public auth base (gateway) for OIDC/SAML callbacks (public-facing host)
    PUBLIC_AUTH_BASE_URL: str = os.getenv("PUBLIC_AUTH_BASE_URL", "https://localhost:3443")
    # Public app base for post-login redirects
    PUBLIC_APP_BASE_URL: str = os.getenv("PUBLIC_APP_BASE_URL", "https://localhost:3443")
    # TLS verification for internal calls to Keycloak (set true outside dev)
    KEYCLOAK_VERIFY_TLS: bool = False
    # Clock skew allowance for token expiration checks (seconds)
    CLOCK_SKEW_SECS: int = int(os.getenv("CLOCK_SKEW_SECS", "120"))
    # State/nonce TTL for replay protection (seconds)
    STATE_TTL_SECS: int = int(os.getenv("STATE_TTL_SECS", "300"))

    # Artifact distribution (placeholders; wire to provisioning later)
    ARTIFACT_ECR_ACCOUNT_ID: str = os.getenv("ARTIFACT_ECR_ACCOUNT_ID", "aws_account_id")
    ARTIFACT_ECR_REGION: str = os.getenv("ARTIFACT_ECR_REGION", "region")
    ARTIFACT_S3_BUCKET: str = os.getenv("ARTIFACT_S3_BUCKET", "sentinelgrid-artifacts")
    ARTIFACT_HELM_BASE_URL: str = os.getenv("ARTIFACT_HELM_BASE_URL", "https://example.com/helm")

    # Endpoint placeholder health (SentinelGuard Go server)
    EDR_API_URL: str = os.getenv("EDR_API_URL") or "http://sentinelguard-server:8085"
    ENDPOINT_HEALTH_URL: str = os.getenv("ENDPOINT_HEALTH_URL") or ""

    # Lifecycle scheduler
    LIFECYCLE_JOB_ENABLED: bool = os.getenv("LIFECYCLE_JOB_ENABLED", "true").lower() == "true"
    LIFECYCLE_JOB_INTERVAL_SECONDS: int = int(os.getenv("LIFECYCLE_JOB_INTERVAL_SECONDS", "300"))

    # Privileged access defaults
    PRIV_ACCESS_TTL_MINUTES: int = int(os.getenv("PRIV_ACCESS_TTL_MINUTES", "60"))

    # Adaptive MFA policy
    MFA_RISK_THRESHOLD: float = float(os.getenv("MFA_RISK_THRESHOLD", "30"))
    MFA_ENFORCED_APPS: list[str] = []
    MFA_ENFORCED_ROLES: list[str] = [
        "TENANT_ADMIN",
        "REALM_ADMIN",
        "ORG_ADMIN",
        "SECURITY_ADMIN",
    ]

    @field_validator("IAM_ROLE_SYNC_REALMS")
    @classmethod
    def _role_sync_realms(cls, values):
        from uuid import UUID
        import re
        result = {}
        for tenant, realm in values.items():
            key = str(UUID(tenant))
            if key in result or realm in {".", ".."} or not re.fullmatch(r"[A-Za-z0-9_.-]{1,255}", realm):
                raise ValueError("Role sync requires unique tenant UUIDs and explicit realm names")
            result[key] = realm
        return result

    @field_validator("KEYCLOAK_ISSUER_BASE_URLS")
    @classmethod
    def _validate_issuer_bases(cls, values):
        normalized = []
        for value in values:
            parsed = urlsplit(value)
            if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                    or parsed.username or parsed.password or parsed.query or parsed.fragment
                    or "/realms/" in parsed.path):
                raise ValueError("KEYCLOAK_ISSUER_BASE_URLS must contain trusted base URLs, without credentials or realm paths")
            normalized.append(value.rstrip("/"))
        return list(dict.fromkeys(normalized))

    @field_validator("MFA_ENFORCED_APPS", "MFA_ENFORCED_ROLES", mode="before")
    @classmethod
    def _split_csv(cls, v):
        """Allow comma-separated env lists for MFA policy knobs."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v or []

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def _normalize_environment(cls, value):
        return normalize_environment(value)

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value):
        return parse_cors_origins(value)

    @model_validator(mode="after")
    def _validate_security_posture(self):
        require_explicit_cors_allowlist(self.ENVIRONMENT, self.CORS_ORIGINS)
        require_https_public_origins(self.ENVIRONMENT, self.CORS_ORIGINS)
        require_non_default_internal_token(self.ENVIRONMENT, self.INTERNAL_SERVICE_TOKEN)

        if self.ENVIRONMENT != "production":
            return self

        if not self.KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT:
            raise ValueError("KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT must be enabled in production")

        if not self.KEYCLOAK_ADMIN_CLIENT_SECRET:
            raise ValueError("KEYCLOAK_ADMIN_CLIENT_SECRET is required when KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT is enabled")

        if not self.KEYCLOAK_ADMIN_CLIENT_ID:
            raise ValueError("KEYCLOAK_ADMIN_CLIENT_ID is required when KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT is enabled")

        for issuer_base in self.KEYCLOAK_ISSUER_BASE_URLS:
            require_secure_service_url(self.ENVIRONMENT, issuer_base, "KEYCLOAK_ISSUER_BASE_URLS", disallowed_hosts=DEFAULT_KEYCLOAK_HOSTS)

        require_tls_verification(self.ENVIRONMENT, self.KEYCLOAK_VERIFY_TLS, "KEYCLOAK_VERIFY_TLS")
        require_tls_verification(self.ENVIRONMENT, self.VAULT_VERIFY_TLS, "VAULT_VERIFY_TLS")
        require_tls_verification(self.ENVIRONMENT, self.UPSTREAM_TLS_VERIFY, "UPSTREAM_TLS_VERIFY")
        require_non_default_database_url(self.ENVIRONMENT, self.DB_URL, "DB_URL")
        if self.IAM_DB_URL:
            require_non_default_database_url(self.ENVIRONMENT, self.IAM_DB_URL, "IAM_DB_URL")
        require_authenticated_redis_url(self.ENVIRONMENT, self.REDIS_URL, "REDIS_URL")
        require_secure_service_url(
            self.ENVIRONMENT,
            self.KEYCLOAK_URL,
            "KEYCLOAK_URL",
            disallowed_hosts=DEFAULT_KEYCLOAK_HOSTS,
        )
        require_secure_service_url(
            self.ENVIRONMENT,
            self.VAULT_ADDR,
            "VAULT_ADDR",
            disallowed_hosts=DEFAULT_VAULT_HOSTS,
        )
        require_secure_service_url(self.ENVIRONMENT, self.PUBLIC_AUTH_BASE_URL, "PUBLIC_AUTH_BASE_URL")
        require_secure_service_url(self.ENVIRONMENT, self.PUBLIC_APP_BASE_URL, "PUBLIC_APP_BASE_URL")

        return self

    # SCIM security
    SCIM_BEARER_TOKEN: Optional[str] = os.getenv("SCIM_BEARER_TOKEN")
    SCIM_TENANT_TOKENS: Optional[str] = os.getenv("SCIM_TENANT_TOKENS")  # JSON or comma-separated tenant:token pairs
    SCIM_DEFAULT_TENANT_ID: str = os.getenv("SCIM_DEFAULT_TENANT_ID", "demo")
    SCIM_RATE_LIMIT_PER_MINUTE: int = int(os.getenv("SCIM_RATE_LIMIT_PER_MINUTE", "60"))
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()


def resolve_keycloak_admin_runtime_auth(
    *,
    environment: Optional[str] = None,
    use_service_account: Optional[bool] = None,
    admin_user: Optional[str] = None,
    admin_password: Optional[str] = None,
    admin_client_id: Optional[str] = None,
    admin_client_secret: Optional[str] = None,
    admin_token_realm: Optional[str] = None,
) -> KeycloakAdminRuntimeAuth:
    """Resolve the Keycloak admin runtime auth mode without allowing implicit fallback."""
    resolved_environment = str(environment or settings.ENVIRONMENT or "development").strip().lower()
    resolved_use_service_account = (
        settings.KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT
        if use_service_account is None
        else use_service_account
    )
    resolved_admin_token_realm = admin_token_realm or settings.KEYCLOAK_ADMIN_TOKEN_REALM
    resolved_admin_client_id = admin_client_id or settings.KEYCLOAK_ADMIN_CLIENT_ID
    resolved_admin_client_secret = admin_client_secret or settings.KEYCLOAK_ADMIN_CLIENT_SECRET
    resolved_admin_user = admin_user or settings.KEYCLOAK_ADMIN_USER
    resolved_admin_password = admin_password or settings.KEYCLOAK_ADMIN_PASSWORD

    if resolved_use_service_account:
        if not resolved_admin_client_id:
            raise KeycloakAdminAuthConfigError(
                "KEYCLOAK_ADMIN_CLIENT_ID is required when service-account auth is enabled"
            )
        if not resolved_admin_client_secret:
            raise KeycloakAdminAuthConfigError(
                "KEYCLOAK_ADMIN_CLIENT_SECRET is required when service-account auth is enabled"
            )
        return KeycloakAdminRuntimeAuth(
            mode="service_account",
            user_realm_name=resolved_admin_token_realm,
            token_payload={
                "grant_type": "client_credentials",
                "client_id": resolved_admin_client_id,
                "client_secret": resolved_admin_client_secret,
            },
            python_keycloak_kwargs={
                "grant_type": "client_credentials",
                "client_id": resolved_admin_client_id,
                "client_secret_key": resolved_admin_client_secret,
            },
        )

    if resolved_environment == "production":
        raise KeycloakAdminAuthConfigError(
            "Password-based Keycloak admin auth is disabled in production; "
            "enable KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT and configure KEYCLOAK_ADMIN_CLIENT_SECRET"
        )

    if not resolved_admin_user or not resolved_admin_password:
        raise KeycloakAdminAuthConfigError(
            "KEYCLOAK_ADMIN_USER and KEYCLOAK_ADMIN_PASSWORD are required when service-account auth is disabled"
        )

    return KeycloakAdminRuntimeAuth(
        mode="password",
        user_realm_name=resolved_admin_token_realm,
        token_payload={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": resolved_admin_user,
            "password": resolved_admin_password,
        },
        python_keycloak_kwargs={
            "username": resolved_admin_user,
            "password": resolved_admin_password,
            "client_id": "admin-cli",
        },
    )
