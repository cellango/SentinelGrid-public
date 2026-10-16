import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _production_kwargs(**overrides):
    base = {
        "ENVIRONMENT": "production",
        "CORS_ORIGINS": ["https://app.sentinelgrid.com"],
        "INTERNAL_SERVICE_TOKEN": "iam-prod-token",
        "KEYCLOAK_URL": "https://identity.sentinelgrid.ai",
        "KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT": True,
        "KEYCLOAK_ADMIN_CLIENT_ID": "iam-agent",
        "KEYCLOAK_ADMIN_CLIENT_SECRET": "svc-secret",
        "KEYCLOAK_VERIFY_TLS": True,
        "VAULT_ADDR": "https://vault.sentinelgrid.ai",
        "VAULT_VERIFY_TLS": True,
        "UPSTREAM_TLS_VERIFY": True,
        "DB_URL": "postgresql://iam:db-secret@db.sentinelgrid.internal:5432/sg",
        "REDIS_URL": "redis://:cache-secret@redis.sentinelgrid.internal:6379/0",
        "PUBLIC_AUTH_BASE_URL": "https://auth.sentinelgrid.ai",
        "PUBLIC_APP_BASE_URL": "https://app.sentinelgrid.ai",
    }
    base.update(overrides)
    return base


def test_cors_origins_supports_csv_input():
    settings = Settings(
        ENVIRONMENT="development",
        CORS_ORIGINS="http://localhost:3000, https://app.sentinelgrid.com",
    )

    assert settings.CORS_ORIGINS == [
        "http://localhost:3000",
        "https://app.sentinelgrid.com",
    ]


def test_production_rejects_default_internal_service_token():
    with pytest.raises(ValidationError, match="INTERNAL_SERVICE_TOKEN"):
        Settings(**_production_kwargs(INTERNAL_SERVICE_TOKEN="internal-service-token-change-in-production"))


def test_production_requires_keycloak_tls_verification():
    with pytest.raises(ValidationError, match="KEYCLOAK_VERIFY_TLS"):
        Settings(**_production_kwargs(KEYCLOAK_VERIFY_TLS=False))


def test_production_requires_service_account_mode_for_keycloak_admin_auth():
    with pytest.raises(ValidationError, match="KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT"):
        Settings(**_production_kwargs(KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT=False))


def test_production_requires_service_account_secret_when_enabled():
    with pytest.raises(ValidationError, match="KEYCLOAK_ADMIN_CLIENT_SECRET"):
        Settings(**_production_kwargs(KEYCLOAK_ADMIN_CLIENT_SECRET=None))


def test_production_accepts_service_account_keycloak_admin_auth():
    settings = Settings(**_production_kwargs())

    assert settings.KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT is True


def test_production_requires_vault_tls_verification():
    with pytest.raises(ValidationError, match="VAULT_VERIFY_TLS"):
        Settings(**_production_kwargs(VAULT_VERIFY_TLS=False))


def test_production_requires_upstream_tls_verification():
    with pytest.raises(ValidationError, match="UPSTREAM_TLS_VERIFY"):
        Settings(**_production_kwargs(UPSTREAM_TLS_VERIFY=False))


def test_production_rejects_localhost_cors_origins():
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(**_production_kwargs(CORS_ORIGINS=["http://localhost:3000"]))


def test_production_requires_non_default_database_url():
    with pytest.raises(ValidationError, match="DB_URL"):
        Settings(**_production_kwargs(DB_URL="postgresql://sg:sg@postgres:5432/sg"))


def test_production_requires_authenticated_redis_url():
    with pytest.raises(ValidationError, match="REDIS_URL"):
        Settings(**_production_kwargs(REDIS_URL="redis://redis.sentinelgrid.internal:6379/0"))


def test_production_rejects_placeholder_keycloak_url():
    with pytest.raises(ValidationError, match="KEYCLOAK_URL"):
        Settings(**_production_kwargs(KEYCLOAK_URL="http://keycloak:8080"))


def test_production_rejects_placeholder_vault_url():
    with pytest.raises(ValidationError, match="VAULT_ADDR"):
        Settings(**_production_kwargs(VAULT_ADDR="http://vault:8200"))


def test_production_rejects_local_public_app_base():
    with pytest.raises(ValidationError, match="PUBLIC_APP_BASE_URL"):
        Settings(**_production_kwargs(PUBLIC_APP_BASE_URL="https://localhost:3443"))
