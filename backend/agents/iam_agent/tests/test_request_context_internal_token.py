"""An opaque shared credential cannot establish an IAM tenant or user."""
from unittest.mock import Mock
import pytest
from fastapi import FastAPI, HTTPException
from starlette.requests import Request
from app.api.request_context import get_current_request_context

@pytest.mark.asyncio
@pytest.mark.parametrize("tenant_hint", [False, True])
async def test_opaque_internal_token_is_not_tenant_authority(tenant_hint):
    headers=[(b"authorization",b"Bearer disposable-local-only")]
    if tenant_hint:headers.append((b"x-tenant-id",b"11111111-1111-4111-8111-111111111111"))
    request=Request({"type":"http","method":"GET","path":"/internal/iam","headers":headers,"app":FastAPI()})
    validator=Mock();validator.validate_token.return_value={"valid":False,"error":"private diagnostic"}
    with pytest.raises(HTTPException) as error:
        await get_current_request_context(request,validator)
    assert error.value.status_code==401 and "private diagnostic" not in error.value.detail
