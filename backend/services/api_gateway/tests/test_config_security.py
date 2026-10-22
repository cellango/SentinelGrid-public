import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_cors_origins_supports_csv_input():
    settings = Settings(
        ENVIRONMENT="development",
        CORS_ORIGINS="http://localhost:3000, https://app.sentinelgrid.com",
    )

    assert settings.CORS_ORIGINS == [
        "http://localhost:3000",
        "https://app.sentinelgrid.com",
    ]


def test_production_rejects_wildcard_cors():
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(
            ENVIRONMENT="production",
            IAM_AGENT_URL="https://iam.sentinelgrid.internal",
            CORS_ORIGINS=["*"],
            INTERNAL_SERVICE_TOKEN="gateway-prod-token",
        )


def test_production_rejects_default_internal_service_token():
    with pytest.raises(ValidationError, match="INTERNAL_SERVICE_TOKEN"):
        Settings(
            ENVIRONMENT="production",
            IAM_AGENT_URL="https://iam.sentinelgrid.internal",
            CORS_ORIGINS=["https://app.sentinelgrid.com"],
            DB_URL="postgresql://gateway:secret@db.sentinelgrid.internal:5432/sg",
            KEYCLOAK_URL="https://identity.sentinelgrid.ai",
        )


def test_production_requires_upstream_tls_verification():
    with pytest.raises(ValidationError, match="UPSTREAM_TLS_VERIFY"):
        Settings(
            ENVIRONMENT="production",
            IAM_AGENT_URL="https://iam.sentinelgrid.internal",
            CORS_ORIGINS=["https://app.sentinelgrid.com"],
            INTERNAL_SERVICE_TOKEN="gateway-prod-token",
            UPSTREAM_TLS_VERIFY=False,
            DB_URL="postgresql://gateway:secret@db.sentinelgrid.internal:5432/sg",
            KEYCLOAK_URL="https://identity.sentinelgrid.ai",
        )


def test_production_rejects_localhost_cors_origins():
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(
            ENVIRONMENT="production",
            IAM_AGENT_URL="https://iam.sentinelgrid.internal",
            CORS_ORIGINS=["https://app.sentinelgrid.com", "http://localhost:3000"],
            INTERNAL_SERVICE_TOKEN="gateway-prod-token",
            UPSTREAM_TLS_VERIFY=True,
            DB_URL="postgresql://gateway:secret@db.sentinelgrid.internal:5432/sg",
            KEYCLOAK_URL="https://identity.sentinelgrid.ai",
        )


def test_production_rejects_default_database_url():
    with pytest.raises(ValidationError, match="DB_URL"):
        Settings(
            ENVIRONMENT="production",
            IAM_AGENT_URL="https://iam.sentinelgrid.internal",
            CORS_ORIGINS=["https://app.sentinelgrid.com"],
            INTERNAL_SERVICE_TOKEN="gateway-prod-token",
            UPSTREAM_TLS_VERIFY=True,
            DB_URL="postgresql://sg:sg@postgres:5432/sg",
            KEYCLOAK_URL="https://identity.sentinelgrid.ai",
        )


def test_production_rejects_default_keycloak_url():
    with pytest.raises(ValidationError, match="KEYCLOAK_URL"):
        Settings(
            ENVIRONMENT="production",
            IAM_AGENT_URL="https://iam.sentinelgrid.internal",
            CORS_ORIGINS=["https://app.sentinelgrid.com"],
            INTERNAL_SERVICE_TOKEN="gateway-prod-token",
            UPSTREAM_TLS_VERIFY=True,
            DB_URL="postgresql://gateway:secret@db.sentinelgrid.internal:5432/sg",
            KEYCLOAK_URL="http://keycloak:8080",
        )



def _production_budgets(**overrides):
    values=dict(ENVIRONMENT='production', IAM_AGENT_URL='https://iam.sentinelgrid.internal',
        CORS_ORIGINS=['https://app.sentinelgrid.com'], INTERNAL_SERVICE_TOKEN='gateway-prod-token',
        UPSTREAM_TLS_VERIFY=True, DB_URL='postgresql://gateway:secret@db.sentinelgrid.internal:5432/sg',
        KEYCLOAK_URL='https://identity.sentinelgrid.ai', RATE_LIMIT_ENABLED=True,
        RATE_LIMIT_FAIL_CLOSED=True,RATE_LIMIT_REDIS_URL='rediss://budget.sentinelgrid.internal:6379/0')
    return Settings(_env_file=None,**{**values,**overrides})


def test_non_development_requires_tls_shared_fail_closed_budgets():
    assert _production_budgets().rate_limit_policy().enabled is True
    for invalid in [{'RATE_LIMIT_ENABLED':False},{'RATE_LIMIT_FAIL_CLOSED':False},
                    {'RATE_LIMIT_REDIS_URL':'redis://budget.sentinelgrid.internal:6379/0'}]:
        with pytest.raises(ValidationError,match='TLS Redis'):
            _production_budgets(**invalid)
