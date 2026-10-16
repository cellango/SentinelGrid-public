"""Auth proxy routes - expose IAM login/refresh via the API Gateway."""

from fastapi import APIRouter, HTTPException, Request, Response
import httpx
from app.core.config import settings

router = APIRouter()


def _build_pre_auth_hint_headers(request: Request) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    for header_name in ("x-tenant-id", "x-realm"):
        header_value = request.headers.get(header_name)
        if header_value:
            headers[header_name] = header_value
    return headers


async def _proxy_pre_auth(request: Request, path: str, error_message: str) -> Response:
    iam_url = f"{settings.IAM_AGENT_URL}{path}"
    try:
        body = await request.json()
    except Exception:
        body = {}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(iam_url, json=body, headers=_build_pre_auth_hint_headers(request))
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"{error_message}: {e}")


@router.post("/login")
async def login(request: Request):
    """Proxy login to IAM Agent so the frontend only calls the gateway."""
    return await _proxy_pre_auth(request, "/api/v1/auth/login", "IAM login proxy failed")


@router.post("/refresh")
async def refresh(request: Request):
    """Proxy refresh-token flow to IAM Agent."""
    return await _proxy_pre_auth(request, "/api/v1/auth/refresh", "IAM refresh proxy failed")
