import hashlib
import os

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.core.security import require_internal_service_token

router = APIRouter(prefix="/internal/provider-keys", tags=["internal"])

PROVIDER_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
}


@router.get("/{org_id}/{provider}")
async def get_provider_key(
    org_id: str,
    provider: str,
    _: str = Depends(require_internal_service_token),
):
    env_var = PROVIDER_ENV_VARS.get(provider)
    if not env_var:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"provider '{provider}' is not configured for internal key fetch",
        )

    api_key = os.getenv(env_var)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{env_var} is not set for org {org_id}",
        )

    return {
        "success": True,
        "key": api_key,
        "key_fingerprint": hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16],
        "message": f"loaded {provider} key from {env_var}",
    }
