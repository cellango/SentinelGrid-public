import sys
import types
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

SERVICE_ROOT = Path(__file__).resolve().parents[1]
LIBS_ROOT = Path(__file__).resolve().parents[3] / "libs"
APP_ROOT = SERVICE_ROOT / "app"

for path in (SERVICE_ROOT, LIBS_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


class _DummyRedisClient:
    def ping(self):
        return True

    def get(self, _key):
        return None

    def setex(self, _key, _ttl, _value):
        return True

    def delete(self, *_keys):
        return 0

    def keys(self, _pattern):
        return []


if "redis" not in sys.modules:
    redis_stub = types.ModuleType("redis")
    redis_stub.from_url = lambda *args, **kwargs: _DummyRedisClient()
    sys.modules["redis"] = redis_stub


def _module_points_to_app_root(module) -> bool:
    app_root = str(APP_ROOT)
    module_file = getattr(module, "__file__", "") or ""
    if module_file and app_root in module_file:
        return True

    module_paths = [str(path) for path in getattr(module, "__path__", [])]
    return any(app_root == module_path or app_root in module_path for module_path in module_paths)


# The monorepo contains several top-level "app" packages. If another service's
# package was imported first, clear it so IAM tests resolve against this service.
existing_app = sys.modules.get("app")
if existing_app and not _module_points_to_app_root(existing_app):
    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name, None)


@pytest.fixture
def iam_test_app():
    from app.api import auth as auth_api

    app = FastAPI()

    @app.get("/")
    async def root():
        return {
            "service": "iam-agent",
            "version": "test",
            "status": "running",
        }

    app.include_router(auth_api.router)
    return app


@pytest.fixture
def iam_test_client(iam_test_app):
    return TestClient(iam_test_app)


@pytest.fixture
def token_payload_factory():
    def _factory(**overrides):
        payload = {
            "sub": "user-123",
            "tenant_id": "tenant-123",
            "user_id": "user-123",
            "email": "user@example.com",
            "roles": ["SOC_ANALYST"],
        }
        payload.update(overrides)
        return payload

    return _factory


@pytest.fixture
def valid_token_validation_result(token_payload_factory):
    def _factory(**overrides):
        payload = token_payload_factory(**overrides.pop("payload_overrides", {}))
        result = {
            "valid": True,
            "payload": payload,
            "tenant_id": payload.get("tenant_id"),
            "user_id": payload.get("user_id"),
            "username": "testuser",
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
            "error": None,
        }
        result.update(overrides)
        return result

    return _factory


@pytest.fixture
def invalid_token_validation_result():
    return {
        "valid": False,
        "payload": None,
        "tenant_id": None,
        "user_id": None,
        "username": None,
        "email": None,
        "roles": [],
        "error": "Invalid token",
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


@pytest.fixture
def mock_keycloak_admin():
    with patch("app.services.realm_manager.KeycloakAdmin") as mock_class:
        admin_instance = Mock()
        mock_class.return_value = admin_instance
        yield admin_instance


@pytest.fixture
def customer_record_factory():
    def _factory(**overrides):
        record = {
            "pricing_tier": "starter",
            "user_count": 10,
            "org_count": 0,
            "has_dedicated_realm": False,
            "name": "SentinelGrid Customer",
        }
        record.update(overrides)
        return record

    return _factory


@pytest.fixture(autouse=True)
def prevent_unintended_database_connections(request):
    """Unit routes must override storage; only the owned cluster suite uses SQL."""
    if request.node.path.name == "test_iam_database.py":
        yield
    else:
        with patch("sqlalchemy.engine.Engine.connect", side_effect=AssertionError(
            "Unit tests must override database dependencies; use test_iam_database for real SQL"
        )):
            yield
