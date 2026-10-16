"""
Adaptive Authentication API endpoints.

Provides risk scoring and policy evaluation for context-aware authentication.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime

from app.services.mfa_policy_service import MFAPolicyService
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth/adaptive", tags=["adaptive-auth"])


# ============================================================================
# Request/Response Models
# ============================================================================

class RiskEvaluationRequest(BaseModel):
    """Risk evaluation request."""
    user_id: str
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    geo_location: Optional[dict] = None
    user_agent: Optional[str] = None


class RiskEvaluationResponse(BaseModel):
    """Risk evaluation response."""
    mfa_required: bool
    reason: str
    risk_score: float
    factors: list[str]
    recommendations: list[str]


# ============================================================================
# Helper Functions
# ============================================================================

async def get_token_data(credentials: str) -> dict:
    """Extract and validate token, return token data with tenant_id."""
    from app.services.token_validator import TokenValidator
    from app.services.keycloak_client import KeycloakClient
    
    keycloak_client = KeycloakClient()
    validator = TokenValidator(keycloak_client)
    result = validator.validate_token(credentials)
    
    if not result.get("valid"):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if not result.get("tenant_id"):
        raise HTTPException(status_code=403, detail="No tenant_id in token")
    
    return result


# ============================================================================
# Adaptive Auth Endpoints
# ============================================================================

@router.post("/evaluate-risk", response_model=RiskEvaluationResponse)
async def evaluate_risk(
    request: RiskEvaluationRequest,
    authorization: str = Depends(lambda req: req.headers.get("authorization", "").replace("Bearer ", ""))
):
    """
    Evaluate authentication risk for a login attempt.
    
    Returns risk score and MFA requirement based on context.
    """
    token_data = await get_token_data(authorization)
    tenant_id = token_data["tenant_id"]
    
    logger.info(f"Risk evaluation for user {request.user_id}")
    
    try:
        policy_service = MFAPolicyService()
        
        result = await policy_service.evaluate_mfa_requirement(
            user_id=request.user_id,
            tenant_id=tenant_id,
            device_id=request.device_id,
            ip_address=request.ip_address,
            geo_location=request.geo_location,
            time_of_day=datetime.utcnow()
        )
        
        # Generate recommendations
        recommendations = []
        if result["risk_score"] > 50:
            recommendations.append("Require MFA for this login")
        if result["risk_score"] > 70:
            recommendations.append("Consider blocking this login attempt")
        if "Untrusted device" in result["factors"]:
            recommendations.append("Register this device as trusted")
        
        return RiskEvaluationResponse(
            mfa_required=result["mfa_required"],
            reason=result["reason"],
            risk_score=result["risk_score"],
            factors=result["factors"],
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error(f"Error evaluating risk: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to evaluate risk")

