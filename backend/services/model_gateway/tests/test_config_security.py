import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_default_runtime_prefers_transformers():
    settings = Settings(
        ENVIRONMENT="development",
        INTERNAL_SERVICE_TOKEN="dev-token",
    )

    assert settings.LLM_RUNTIME == "transformers"


def test_production_rejects_default_internal_service_token():
    with pytest.raises(ValidationError, match="INTERNAL_SERVICE_TOKEN"):
        Settings(
            ENVIRONMENT="production",
            MODEL_GATEWAY_DATABASE_URL="postgresql://modelgw:secret@db.sentinelgrid.internal:5432/sg",
            REDIS_URL="redis://:cache-secret@redis.sentinelgrid.internal:6379/0",
        )


def test_production_rejects_default_database_url():
    with pytest.raises(ValidationError, match="MODEL_GATEWAY_DATABASE_URL"):
        Settings(
            ENVIRONMENT="production",
            INTERNAL_SERVICE_TOKEN="model-gateway-prod-token",
            MODEL_GATEWAY_DATABASE_URL="postgresql://sg:sg@localhost:5432/sg",
            REDIS_URL="redis://:cache-secret@redis.sentinelgrid.internal:6379/0",
        )


def test_production_rejects_unauthenticated_redis_url():
    with pytest.raises(ValidationError, match="REDIS_URL"):
        Settings(
            ENVIRONMENT="production",
            INTERNAL_SERVICE_TOKEN="model-gateway-prod-token",
            MODEL_GATEWAY_DATABASE_URL="postgresql://modelgw:secret@db.sentinelgrid.internal:5432/sg",
            REDIS_URL="redis://redis.sentinelgrid.internal:6379/0",
        )


def test_production_accepts_non_default_backing_services():
    settings = Settings(
        ENVIRONMENT="production",
        INTERNAL_SERVICE_TOKEN="model-gateway-prod-token",
        MODEL_GATEWAY_DATABASE_URL="postgresql://modelgw:secret@db.sentinelgrid.internal:5432/sg",
        REDIS_URL="redis://:cache-secret@redis.sentinelgrid.internal:6379/0",
    )

    assert settings.MODEL_GATEWAY_DATABASE_URL.endswith("/sg")
