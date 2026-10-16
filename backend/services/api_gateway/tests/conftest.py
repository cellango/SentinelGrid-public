"""
Pytest configuration and fixtures for API Gateway tests.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from types import SimpleNamespace
from uuid import uuid4
import json
import httpx
import sys
import os

# Add libs directory to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../libs")
sys.path.insert(0, libs_path)

# The PR workflow executes the merge commit against origin/main, where the API
# gateway includes Redis-backed rate limiting. Disable it in tests so auth and
# proxy contract assertions are not rewritten into 429s when Redis is absent.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_FAIL_CLOSED", "false")

from app.main import app


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return Mock()


@pytest.fixture
def mock_get_db(mock_db_session):
    """Mock get_db dependency."""
    def _get_db():
        yield mock_db_session
    return _get_db


@pytest.fixture
def mock_get_tenant_session(mock_db_session):
    """Mock tenant-scoped DB dependency."""
    def _get_db():
        yield mock_db_session
    return _get_db


@pytest.fixture
def mock_get_current_tenant():
    """Mock get_current_tenant dependency."""
    def _get_tenant():
        return "tenant-123"
    return _get_tenant


@pytest.fixture
def client(mock_get_db, mock_get_tenant_session, mock_get_current_tenant):
    """FastAPI test client with mocked dependencies."""
    # Override dependencies
    from sg_core.db import get_db, get_tenant_session
    from sg_core.security import get_current_tenant
    
    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_tenant_session] = mock_get_tenant_session
    app.dependency_overrides[get_current_tenant] = mock_get_current_tenant
    
    yield TestClient(app)
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(mock_get_db, mock_get_tenant_session):
    """FastAPI test client that uses the real auth dependency but mocked DB."""
    from sg_core.db import get_db, get_tenant_session

    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_tenant_session] = mock_get_tenant_session

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def mock_token_payload():
    """Mock JWT token payload."""
    return {
        "sub": "user-123",
        "tenant_id": "tenant-123",
        "realm_roles": ["user", "admin"],
        "email": "user@example.com"
    }


@pytest.fixture
def token_payload_factory():
    """Factory for building JWT-like payloads with tenant context."""

    def _factory(**overrides):
        payload = {
            "sub": "user-123",
            "tenant_id": "tenant-123",
            "realm_roles": ["user", "admin"],
            "email": "user@example.com",
        }
        payload.update(overrides)
        return payload

    return _factory


@pytest.fixture
def invalid_token_validation_result():
    return {"valid": False, "error": "Invalid token"}


@pytest.fixture
def missing_tenant_token_validation_result(token_payload_factory):
    return {"valid": True, "payload": token_payload_factory(tenant_id=None)}


@pytest.fixture
def proxy_response_factory():
    """Build lightweight upstream responses for proxy route tests."""

    def _factory(
        *,
        status_code=200,
        payload=None,
        content=None,
        headers=None,
    ):
        if content is None:
            if payload is None:
                payload = {}
            content = json.dumps(payload).encode()
        elif isinstance(content, str):
            content = content.encode()
        return SimpleNamespace(
            status_code=status_code,
            content=content,
            headers=headers or {"content-type": "application/json"},
        )

    return _factory


@pytest.fixture
def proxy_async_client_factory(monkeypatch, proxy_response_factory):
    """Patch an async client on a target module and capture outbound proxy calls."""

    def _factory(target_module, *, responses=None, exception=None):
        calls = []
        queued_responses = list(responses or [proxy_response_factory()])

        def _consume_response():
            if exception is not None:
                raise exception
            if queued_responses:
                next_item = queued_responses.pop(0)
                if isinstance(next_item, Exception):
                    raise next_item
                return next_item
            return proxy_response_factory()

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def get(self, url, headers=None, params=None):
                calls.append(
                    {
                        "method": "GET",
                        "url": url,
                        "headers": headers or {},
                        "params": params,
                    }
                )
                return _consume_response()

            async def post(self, url, json=None, headers=None, content=None):
                calls.append(
                    {
                        "method": "POST",
                        "url": url,
                        "json": json,
                        "headers": headers or {},
                        "content": content,
                    }
                )
                return _consume_response()

        monkeypatch.setattr(target_module.httpx, "AsyncClient", FakeAsyncClient)
        return calls

    return _factory


@pytest.fixture
def tenant_header_matrix():
    return {
        "x-tenant-id": "tenant-123",
        "x-realm": "realm-123",
    }


@pytest.fixture
def tenant_pair():
    return str(uuid4()), str(uuid4())


@pytest.fixture
def foreign_tenant_pair(tenant_pair):
    primary, foreign = tenant_pair
    return {
        "authenticated": primary,
        "foreign": foreign,
    }
