"""Pre-authentication login/refresh routing; hints never grant identity."""
from fastapi import APIRouter, Request
from app.core.config import settings
from app.core.proxy import proxy_request

router = APIRouter()

async def _proxy_pre_auth(request: Request, path: str, error_message: str):
    return await proxy_request(request, origin=settings.IAM_AGENT_URL, prefix=path, pre_auth=True)

@router.post("/login")
async def login(request: Request):
    return await _proxy_pre_auth(request, "/api/v1/auth/login", "Upstream service unavailable")

@router.post("/refresh")
async def refresh(request: Request):
    return await _proxy_pre_auth(request, "/api/v1/auth/refresh", "Upstream service unavailable")
