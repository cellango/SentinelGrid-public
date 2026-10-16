from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_api_key, require_internal_service_token
from app import models

router = APIRouter(prefix="/internal/auth", tags=["internal-auth"])


class ValidateApiKeyRequest(BaseModel):
    api_key: str


@router.post("/validate-api-key")
def validate_api_key(
    payload: ValidateApiKeyRequest,
    _: str = Depends(require_internal_service_token),
    db: Session = Depends(get_db),
):
    hashed_key = hash_api_key(payload.api_key)
    app = db.query(models.AiApp).filter(models.AiApp.api_key_hash == hashed_key).first()
    if not app:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid api key",
        )

    return {
        "valid": True,
        "org_id": str(app.org_id),
        "app_id": str(app.id),
        "realm": app.environment,
        "app_name": app.name,
    }
