"""API endpoints for phishing email analysis."""

import sys
import os
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

# Add libs to path
libs_path = os.path.join(os.path.dirname(__file__), "../../../../libs")
if os.path.exists(libs_path):
    sys.path.insert(0, libs_path)

from app.services.phishing_analyzer import PhishingAnalyzer
from app.core.config import settings

router = APIRouter(prefix="/api/v1/orchestrator", tags=["phishing"])


class PhishingAnalysisRequest(BaseModel):
    """Request for phishing email analysis."""
    phishing_report_id: UUID
    tenant_id: UUID
    force_reanalyze: Optional[bool] = False


class PhishingAnalysisResponse(BaseModel):
    """Response from phishing analysis."""
    phishing_report_id: UUID
    classification: str  # 'phishing', 'benign', 'suspicious'
    confidence: float  # 0-100
    reasoning: str
    indicators: dict  # URLs, domains, IPs, emails
    recommended_actions: list
    mitre_mapping: dict  # tactics and techniques
    nist_mapping: dict  # controls
    severity: Optional[str] = None


@router.post("/analyze-phishing-email", response_model=PhishingAnalysisResponse)
async def analyze_phishing_email(
    request: PhishingAnalysisRequest
):
    """
    Analyze a phishing email using AI.
    
    This endpoint:
    1. Fetches the phishing report
    2. Calls Model Gateway for AI analysis
    3. Extracts observables
    4. Maps to MITRE/NIST frameworks
    5. Stores results in database
    """
    try:
        analyzer = PhishingAnalyzer()
        result = await analyzer.analyze_phishing_email(
            tenant_id=request.tenant_id,
            phishing_report_id=request.phishing_report_id,
            force_reanalyze=request.force_reanalyze
        )
        
        return PhishingAnalysisResponse(
            phishing_report_id=result["phishing_report_id"],
            classification=result["classification"],
            confidence=result["confidence"],
            reasoning=result["reasoning"],
            indicators=result["indicators"],
            recommended_actions=result["recommended_actions"],
            mitre_mapping=result["mitre_mapping"],
            nist_mapping=result["nist_mapping"],
            severity=result.get("severity")
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing phishing email: {str(e)}")

