from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api import request_context as request_context_module


class _UnexpectedValidator:
    def validate_token(self, _token):
        raise AssertionError("validator should not run for internal service token requests")


def _request(headers: dict[str, str]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/iam/dashboard-snapshot",
            "headers": [(key.lower().encode("utf-8"), value.encode("utf-8")) for key, value in headers.items()],
        }
    )


@pytest.mark.asyncio
async def test_request_context_accepts_internal_service_token_with_tenant_header(monkeypatch):
    monkeypatch.setattr(request_context_module.settings, "INTERNAL_SERVICE_TOKEN", "internal-token")

    result = await request_context_module.get_current_request_context(
        request=_request(
            {
                "Authorization": "Bearer internal-token",
                "X-Tenant-ID": "11111111-1111-1111-1111-111111111111",
            }
        ),
        validator=_UnexpectedValidator(),
    )

    assert result.tenant_id == UUID("11111111-1111-1111-1111-111111111111")
    assert result.roles == ("INTERNAL_SERVICE",)
    assert result.user_id is None


@pytest.mark.asyncio
async def test_request_context_rejects_internal_service_token_without_tenant_header(monkeypatch):
    monkeypatch.setattr(request_context_module.settings, "INTERNAL_SERVICE_TOKEN", "internal-token")

    with pytest.raises(HTTPException, match="X-Tenant-ID header is required"):
        await request_context_module.get_current_request_context(
            request=_request({"Authorization": "Bearer internal-token"}),
            validator=_UnexpectedValidator(),
        )
