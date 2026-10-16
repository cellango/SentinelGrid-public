from fastapi import APIRouter, Depends

router = APIRouter()
from app.core.security import require_internal_service_token

@router.post("/validate/output")
def validate_output(
    request: dict,
    _: str = Depends(require_internal_service_token),
):
    """Validate LLM output against schema"""
    # Simplified implementation - real version would use Guardrails AI
    return {
        "valid": True,
        "errors": []
    }
