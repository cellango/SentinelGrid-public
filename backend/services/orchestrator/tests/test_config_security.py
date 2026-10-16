import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_default_database_url():
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(
            ENVIRONMENT="production",
            CORS_ORIGINS=["https://app.sentinelgrid.com"],
            INTERNAL_SERVICE_TOKEN="orchestrator-prod-token",
            UPSTREAM_TLS_VERIFY=True,
            DATABASE_URL="postgresql://sg:sg@postgres:5432/sg",
        )


def test_production_accepts_non_default_database_url():
    settings = Settings(
        ENVIRONMENT="production",
        CORS_ORIGINS=["https://app.sentinelgrid.com"],
        INTERNAL_SERVICE_TOKEN="orchestrator-prod-token",
        UPSTREAM_TLS_VERIFY=True,
        DATABASE_URL="postgresql://orchestrator:secret@db.sentinelgrid.internal:5432/sg",
    )

    assert settings.DATABASE_URL.endswith("/sg")
