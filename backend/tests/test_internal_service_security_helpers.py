from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException


REPO_ROOT = Path(__file__).resolve().parents[2]
LIBS_ROOT = REPO_ROOT / "backend" / "libs"
if str(LIBS_ROOT) not in sys.path:
    sys.path.insert(0, str(LIBS_ROOT))

from sg_core.service_security import (  # noqa: E402
    build_internal_auth_headers,
    resolve_internal_service_token,
    verify_internal_service_token,
)


def test_build_internal_auth_headers_uses_bearer_and_tenant_scope():
    headers = build_internal_auth_headers(
        "internal-prod-token",
        tenant_id="11111111-1111-1111-1111-111111111111",
        extra_headers={"X-Request-ID": "req-123"},
    )

    assert headers == {
        "X-Request-ID": "req-123",
        "Authorization": "Bearer internal-prod-token",
        "X-Tenant-ID": "11111111-1111-1111-1111-111111111111",
    }


def test_verify_internal_service_token_accepts_authorization_bearer():
    token = verify_internal_service_token(
        "internal-prod-token",
        authorization="Bearer internal-prod-token",
    )

    assert token == "internal-prod-token"


def test_verify_internal_service_token_accepts_legacy_internal_header():
    token = verify_internal_service_token(
        "internal-prod-token",
        x_internal_service_token="internal-prod-token",
    )

    assert token == "internal-prod-token"


def test_resolve_internal_service_token_rejects_conflicting_headers():
    with pytest.raises(HTTPException, match="Conflicting internal service authentication headers"):
        resolve_internal_service_token(
            authorization="Bearer internal-prod-token",
            x_internal_service_token="different-token",
        )
