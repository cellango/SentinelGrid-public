from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

import app.services.keycloak_client as keycloak_client_module
import app.services.token_validator as token_validator_module
import app.services.vault_client as vault_client_module
from app.core.config import KeycloakAdminAuthConfigError
from app.services.keycloak_admin_client import KeycloakAdminClient
from app.services.keycloak_client import KeycloakClient, KeycloakRoleClient
from app.services.keycloak_seeder import KeycloakSeeder
from app.services.token_validator import TokenValidator
from app.services.vault_client import VaultClient


@pytest.mark.asyncio
async def test_keycloak_admin_client_uses_service_account_grant_payload():
    client = KeycloakAdminClient(
        server_url="https://keycloak.internal",
        admin_user="admin",
        admin_password="password",
        admin_client_id="iam-agent",
        admin_client_secret="svc-secret",
        admin_token_realm="ops",
        use_service_account=True,
        verify_tls=True,
    )
    mock_http_client = AsyncMock()
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = {
        "access_token": "service-account-token",
        "expires_in": 60,
    }
    mock_http_client.post.return_value = mock_response

    with patch.object(client, "_get_client", return_value=mock_http_client):
        token = await client._get_admin_token()

    assert token == "service-account-token"
    assert mock_http_client.post.call_args.args[0] == (
        "https://keycloak.internal/realms/ops/protocol/openid-connect/token"
    )
    assert mock_http_client.post.call_args.kwargs["data"] == {
        "grant_type": "client_credentials",
        "client_id": "iam-agent",
        "client_secret": "svc-secret",
    }


def test_keycloak_admin_client_http_client_respects_verify_tls():
    with patch("app.services.keycloak_admin_client.httpx.AsyncClient") as mock_async_client:
        client = KeycloakAdminClient(
            server_url="https://keycloak.internal",
            verify_tls=True,
        )

        http_client = client._get_client()

    assert http_client is mock_async_client.return_value
    assert mock_async_client.call_args.kwargs["verify"] is True


@pytest.mark.asyncio
async def test_keycloak_role_client_uses_service_account_grant_and_verify_tls():
    mock_http_client = AsyncMock()
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = {
        "access_token": "role-client-token",
        "expires_in": 60,
    }
    mock_http_client.post.return_value = mock_response

    with patch("app.services.keycloak_client.httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_http_client
        client = KeycloakRoleClient(
            server_url="https://keycloak.internal",
            realm="sentinelgrid",
            admin_client_id="iam-agent",
            admin_client_secret="svc-secret",
            admin_token_realm="ops",
            use_service_account=True,
            verify_tls=True,
        )

        token = await client._get_admin_token()

    assert token == "role-client-token"
    assert mock_async_client.call_args.kwargs["verify"] is True
    assert mock_http_client.post.call_args.args[0] == (
        "https://keycloak.internal/realms/ops/protocol/openid-connect/token"
    )
    assert mock_http_client.post.call_args.kwargs["data"] == {
        "grant_type": "client_credentials",
        "client_id": "iam-agent",
        "client_secret": "svc-secret",
    }


def test_keycloak_admin_client_rejects_missing_service_account_secret():
    with pytest.raises(KeycloakAdminAuthConfigError, match="KEYCLOAK_ADMIN_CLIENT_SECRET"):
        KeycloakAdminClient(
            server_url="https://keycloak.internal",
            admin_client_id="iam-agent",
            admin_client_secret=None,
            use_service_account=True,
            verify_tls=True,
        )


def test_keycloak_role_client_rejects_password_grant_in_production():
    with (
        patch.object(keycloak_client_module.settings, "ENVIRONMENT", "production"),
        patch.object(keycloak_client_module.settings, "KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT", False),
    ):
        with pytest.raises(KeycloakAdminAuthConfigError, match="disabled in production"):
            KeycloakRoleClient(
                server_url="https://keycloak.internal",
                realm="sentinelgrid",
                admin_user="admin",
                admin_password="rotated-secret",
                use_service_account=False,
                verify_tls=True,
            )


def test_keycloak_client_initialization_uses_service_account_settings():
    with (
        patch("app.services.keycloak_client.KeycloakAdmin") as mock_admin,
        patch.object(keycloak_client_module.settings, "KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT", True),
        patch.object(keycloak_client_module.settings, "KEYCLOAK_ADMIN_CLIENT_SECRET", "svc-secret"),
        patch.object(keycloak_client_module.settings, "KEYCLOAK_ADMIN_CLIENT_ID", "iam-agent"),
        patch.object(keycloak_client_module.settings, "KEYCLOAK_ADMIN_TOKEN_REALM", "ops"),
        patch.object(keycloak_client_module.settings, "KEYCLOAK_VERIFY_TLS", True),
        patch.object(keycloak_client_module.settings, "KEYCLOAK_URL", "https://keycloak.internal"),
        patch.object(keycloak_client_module.settings, "KEYCLOAK_REALM", "sentinelgrid"),
    ):
        KeycloakClient()

    assert mock_admin.call_args.kwargs["grant_type"] == "client_credentials"
    assert mock_admin.call_args.kwargs["client_id"] == "iam-agent"
    assert mock_admin.call_args.kwargs["client_secret_key"] == "svc-secret"
    assert mock_admin.call_args.kwargs["verify"] is True
    assert mock_admin.call_args.kwargs["user_realm_name"] == "ops"


def test_keycloak_client_rejects_password_grant_in_production():
    with (
        patch.object(keycloak_client_module.settings, "ENVIRONMENT", "production"),
        patch.object(keycloak_client_module.settings, "KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT", False),
        patch("app.services.keycloak_client.KeycloakAdmin"),
    ):
        with pytest.raises(KeycloakAdminAuthConfigError, match="disabled in production"):
            KeycloakClient()


def test_keycloak_seeder_get_admin_token_uses_service_account_payload():
    with (
        patch.object(keycloak_client_module.settings, "KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT", True),
        patch.object(keycloak_client_module.settings, "KEYCLOAK_ADMIN_CLIENT_ID", "iam-agent"),
        patch.object(keycloak_client_module.settings, "KEYCLOAK_ADMIN_CLIENT_SECRET", "svc-secret"),
        patch.object(keycloak_client_module.settings, "KEYCLOAK_ADMIN_TOKEN_REALM", "ops"),
        patch.object(keycloak_client_module.settings, "KEYCLOAK_VERIFY_TLS", True),
        patch.object(keycloak_client_module.settings, "KEYCLOAK_URL", "https://keycloak.internal"),
        patch.object(keycloak_client_module.settings, "KEYCLOAK_REALM", "sentinelgrid"),
        patch.object(keycloak_client_module.settings, "ENVIRONMENT", "production"),
        patch("app.services.keycloak_seeder.KeycloakSeeder._init_admin_client", return_value=None),
        patch("httpx.post") as mock_http_post,
    ):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "seed-token"}
        mock_http_post.return_value = mock_response

        seeder = KeycloakSeeder()
        token = seeder._get_admin_token()

    assert token == "seed-token"
    assert mock_http_post.call_args.args[0] == (
        "https://keycloak.internal/realms/ops/protocol/openid-connect/token"
    )
    assert mock_http_post.call_args.kwargs["data"] == {
        "grant_type": "client_credentials",
        "client_id": "iam-agent",
        "client_secret": "svc-secret",
    }


def test_token_validator_fetches_jwks_with_keycloak_tls_verification():
    mock_keycloak_client = Mock(spec=KeycloakClient)
    validator = TokenValidator(mock_keycloak_client)
    mock_http_client = Mock()
    mock_response = Mock()
    mock_response.raise_for_status = Mock()
    mock_response.json.return_value = {"keys": [{"kid": "test"}]}
    mock_http_client.get.return_value = mock_response

    with (
        patch("app.services.token_validator.httpx.Client") as mock_client_cls,
        patch.object(token_validator_module.settings, "KEYCLOAK_VERIFY_TLS", True),
    ):
        mock_client_cls.return_value.__enter__.return_value = mock_http_client
        jwks = validator._get_jwks_for_realm("demo")

    assert jwks == {"keys": [{"kid": "test"}]}
    assert mock_client_cls.call_args.kwargs["verify"] is True


def test_vault_client_uses_configured_tls_verification():
    with (
        patch("app.services.vault_client.httpx.Client") as mock_client_cls,
        patch.object(vault_client_module.settings, "VAULT_VERIFY_TLS", True),
    ):
        client = VaultClient(
            addr="https://vault.internal",
            token="vault-token",
            mount="secret",
        )

    assert client._client is mock_client_cls.return_value
    assert mock_client_cls.call_args.kwargs["verify"] is True


def test_reusable_iam_service_clients_do_not_hardcode_verify_false():
    repo_root = Path(__file__).resolve().parents[4]
    service_files = [
        "backend/agents/iam_agent/app/services/keycloak_admin_client.py",
        "backend/agents/iam_agent/app/services/keycloak_client.py",
        "backend/agents/iam_agent/app/services/token_validator.py",
        "backend/agents/iam_agent/app/services/vault_client.py",
    ]

    for relative_path in service_files:
        content = (repo_root / relative_path).read_text()
        assert "verify=False" not in content
