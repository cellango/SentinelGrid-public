import re
from fastapi import APIRouter, Depends
from app import schemas
from app.core.security import require_internal_service_token

router = APIRouter()

# Secret patterns
SECRET_PATTERNS = {
    "api_key": r"(?i)(api[_-]?key|apikey)[\s:=]+['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
    "password": r"(?i)(password|passwd|pwd)[\s:=]+['\"]?([^\s'\"]{8,})['\"]?",
    "token": r"(?i)(token|auth|bearer)[\s:=]+['\"]?([a-zA-Z0-9_\-\.]{20,})['\"]?",
    "aws_key": r"(?i)(aws_access_key_id|aws_secret_access_key)[\s:=]+['\"]?([A-Z0-9]{20,})['\"]?",
    "private_key": r"-----BEGIN [A-Z ]+PRIVATE KEY-----",
}

@router.post("/scan/secrets", response_model=schemas.SecretsScanResponse)
def scan_secrets(
    request: schemas.SecretsScanRequest,
    _: str = Depends(require_internal_service_token),
):
    """Scan text for secrets"""
    text = request.text
    
    findings = []
    for secret_type, pattern in SECRET_PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            findings.append(f"{secret_type}_detected")
    
    return schemas.SecretsScanResponse(
        has_secrets=len(findings) > 0,
        findings=findings
    )
