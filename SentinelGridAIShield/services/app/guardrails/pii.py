from fastapi import APIRouter, Depends
from app import schemas
from app.core.security import require_internal_service_token

router = APIRouter()

@router.post("/scan/pii", response_model=schemas.PIIScanResponse)
def scan_pii(
    request: schemas.PIIScanRequest,
    _: str = Depends(require_internal_service_token),
):
    """Scan text for PII using Presidio"""
    # Simplified implementation - real version would use Presidio
    text = request.text
    
    # Simple pattern matching for demo
    has_pii = False
    entities = []
    redacted = text
    
    # Check for email patterns
    if "@" in text and "." in text:
        has_pii = True
        entities.append("EMAIL")
        # Simple redaction
        words = text.split()
        redacted = " ".join(["[EMAIL]" if "@" in w else w for w in words])
    
    # Check for SSN patterns
    if any(c.isdigit() for c in text) and "-" in text:
        has_pii = True
        entities.append("SSN")
    
    # Check for credit card patterns
    if len([c for c in text if c.isdigit()]) >= 13:
        has_pii = True
        entities.append("CREDIT_CARD")
    
    return schemas.PIIScanResponse(
        has_pii=has_pii,
        entities=list(set(entities)),
        redacted=redacted
    )
