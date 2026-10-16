import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_default_database_url():
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(
            ENVIRONMENT="production",
            CORS_ORIGINS=["https://app.sentinelgrid.com"],
            INTERNAL_SERVICE_TOKEN="siem-prod-token",
            UPSTREAM_TLS_VERIFY=True,
            OPENSEARCH_USE_SSL=True,
            OPENSEARCH_VERIFY_CERTS=True,
            OPENSEARCH_URL="https://search.sentinelgrid.ai",
            REDIS_URL="redis://:cache-secret@redis.sentinelgrid.internal:6379/0",
            DB_HOST="postgres",
            DB_NAME="sg",
            DB_USER="sg",
            DB_PASSWORD="sg",
        )


def test_production_rejects_unauthenticated_redis_url():
    with pytest.raises(ValidationError, match="REDIS_URL"):
        Settings(
            ENVIRONMENT="production",
            CORS_ORIGINS=["https://app.sentinelgrid.com"],
            INTERNAL_SERVICE_TOKEN="siem-prod-token",
            UPSTREAM_TLS_VERIFY=True,
            OPENSEARCH_USE_SSL=True,
            OPENSEARCH_VERIFY_CERTS=True,
            OPENSEARCH_URL="https://search.sentinelgrid.ai",
            REDIS_URL="redis://redis.sentinelgrid.internal:6379/0",
            DB_HOST="db.sentinelgrid.internal",
            DB_NAME="sg",
            DB_USER="siem",
            DB_PASSWORD="db-secret",
        )


def test_production_rejects_default_opensearch_url():
    with pytest.raises(ValidationError, match="OPENSEARCH_URL"):
        Settings(
            ENVIRONMENT="production",
            CORS_ORIGINS=["https://app.sentinelgrid.com"],
            INTERNAL_SERVICE_TOKEN="siem-prod-token",
            UPSTREAM_TLS_VERIFY=True,
            OPENSEARCH_USE_SSL=True,
            OPENSEARCH_VERIFY_CERTS=True,
            OPENSEARCH_URL="http://opensearch:9200",
            REDIS_URL="redis://:cache-secret@redis.sentinelgrid.internal:6379/0",
            DB_HOST="db.sentinelgrid.internal",
            DB_NAME="sg",
            DB_USER="siem",
            DB_PASSWORD="db-secret",
        )


def test_production_accepts_non_default_backing_services():
    settings = Settings(
        ENVIRONMENT="production",
        CORS_ORIGINS=["https://app.sentinelgrid.com"],
        INTERNAL_SERVICE_TOKEN="siem-prod-token",
        UPSTREAM_TLS_VERIFY=True,
        OPENSEARCH_USE_SSL=True,
        OPENSEARCH_VERIFY_CERTS=True,
        OPENSEARCH_URL="https://search.sentinelgrid.ai",
        REDIS_URL="redis://:cache-secret@redis.sentinelgrid.internal:6379/0",
        DB_HOST="db.sentinelgrid.internal",
        DB_NAME="sg",
        DB_USER="siem",
        DB_PASSWORD="db-secret",
    )

    assert settings.DATABASE_URL.endswith("/sg")
