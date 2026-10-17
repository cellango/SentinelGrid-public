"""Legacy token/header helpers cannot grant ingestion workload authority."""

import asyncio
import pytest
from fastapi import HTTPException
from starlette.requests import Request
from app.core import security


@pytest.mark.parametrize(
    "token", ["dev-token", "synthetic-static-token", "malformed.jwt"]
)
def test_legacy_token_only_helper_is_unavailable(token):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(security.verify_token_with_iam_agent(token))
    assert exc.value.status_code == 503


@pytest.mark.parametrize(
    "headers",
    [
        [],
        [(b"x-tenant-id", b"11111111-1111-4111-8111-111111111111")],
        [(b"authorization", b"Bearer dev-token")],
    ],
)
def test_legacy_tenant_dependency_cannot_use_raw_headers(headers):
    request = Request({"type": "http", "headers": headers})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(security.get_current_tenant(request))
    assert exc.value.status_code == 503
    assert not hasattr(request.state, "tenant_id")
