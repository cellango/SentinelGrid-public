"""Shared Keycloak admin client factory.

Uses service-account authentication in production and allows the legacy
admin user/password flow only in non-production environments.
"""

from typing import Optional

from keycloak import KeycloakAdmin

from app.core.config import resolve_keycloak_admin_runtime_auth, settings


def build_keycloak_admin(
    *,
    realm_name: str = "master",
    server_url: Optional[str] = None,
    verify_tls: Optional[bool] = None,
    use_service_account: Optional[bool] = None,
    admin_user: Optional[str] = None,
    admin_password: Optional[str] = None,
    admin_client_id: Optional[str] = None,
    admin_client_secret: Optional[str] = None,
    admin_token_realm: Optional[str] = None,
) -> KeycloakAdmin:
    """Create a KeycloakAdmin instance with the configured auth mode."""
    resolved_server_url = (server_url or settings.KEYCLOAK_URL).rstrip("/") + "/"
    resolved_verify_tls = settings.KEYCLOAK_VERIFY_TLS if verify_tls is None else verify_tls
    resolved_use_service_account = (
        settings.KEYCLOAK_ADMIN_USE_SERVICE_ACCOUNT
        if use_service_account is None
        else use_service_account
    )
    admin_auth = resolve_keycloak_admin_runtime_auth(
        use_service_account=resolved_use_service_account,
        admin_user=admin_user,
        admin_password=admin_password,
        admin_client_id=admin_client_id,
        admin_client_secret=admin_client_secret,
        admin_token_realm=admin_token_realm,
    )

    admin_kwargs = {
        "server_url": resolved_server_url,
        "realm_name": realm_name,
        "user_realm_name": admin_auth.user_realm_name,
        "verify": resolved_verify_tls,
    }
    admin_kwargs.update(admin_auth.python_keycloak_kwargs)

    return KeycloakAdmin(**admin_kwargs)
