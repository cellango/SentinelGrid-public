from fastapi import APIRouter, Depends
from app import schemas
from app.core.security import require_internal_service_token

router = APIRouter()

# Common prompt injection patterns
INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore above",
    "disregard previous",
    "forget everything",
    "new instructions",
    "system prompt",
    "you are now",
    "act as",
    "pretend you are",
    "jailbreak"
]

@router.post("/scan/injection", response_model=schemas.InjectionScanResponse)
def scan_injection(
    request: schemas.InjectionScanRequest,
    _: str = Depends(require_internal_service_token),
):
    """Scan text for prompt injection attempts"""
    # Simplified implementation - real version would use LLM Guard
    text = request.text.lower()
    
    detected_patterns = []
    for pattern in INJECTION_PATTERNS:
        if pattern in text:
            detected_patterns.append(pattern)
    
    score = min(len(detected_patterns) * 0.3, 1.0)
    is_suspicious = score > 0.5
    
    return schemas.InjectionScanResponse(
        is_suspicious=is_suspicious,
        score=score,
        patterns=detected_patterns
    )
