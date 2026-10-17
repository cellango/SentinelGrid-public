"""Legacy callback state helpers cannot open unscoped or raw-UUID sessions."""

import pytest
from fastapi import HTTPException
from app.api.connectors import (
    OAuthCallbackRequest,
    resolve_oauth_callback_tenant,
    get_oauth_callback_tenant_session,
)


def test_oauth_state_is_not_standalone_tenant_authority():
    with pytest.raises(HTTPException) as exc:
        resolve_oauth_callback_tenant(
            OAuthCallbackRequest(
                provider="google_workspace", code="synthetic", state="synthetic"
            )
        )
    assert exc.value.status_code == 503
    with pytest.raises(HTTPException) as exc:
        next(get_oauth_callback_tenant_session())
    assert exc.value.status_code == 503
