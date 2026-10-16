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
            CORS_ORIGINS=["*"],
            INTERNAL_SERVICE_TOKEN="soar-prod-token",
        )


def test_production_rejects_default_internal_service_token():
    with pytest.raises(ValidationError, match="INTERNAL_SERVICE_TOKEN"):
        Settings(
            ENVIRONMENT="production",
            CORS_ORIGINS=["https://app.sentinelgrid.com"],
        )
