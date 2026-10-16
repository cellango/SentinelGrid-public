"""Posture Platform proxy routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))

from sg_core.security import get_current_tenant
from sg_core.request_tracing import build_trace_headers
from sg_core.service_security import build_internal_auth_headers
from app.core.config import settings

router = APIRouter()

# Posture platform services
ANALYZER_ORCHESTRATOR_URL = os.getenv("ANALYZER_ORCHESTRATOR_URL", "http://analyzer-orchestrator:8000")
POSTURE_SERVICE_URL = os.getenv("POSTURE_SERVICE_URL", "http://posture-service:8000")


class AnalyzeObservableRequest(BaseModel):
    """Request to analyze an observable."""
    observable_type: str
    observable_value: str
    metadata: Optional[Dict[str, Any]] = None
    analyzer_tags: Optional[List[str]] = None


@router.post("/analyze")
async def analyze_observable(
    request: AnalyzeObservableRequest,
    current_tenant_id: str = Depends(get_current_tenant),
):
    """
    Trigger analysis of an observable (asset, repo, image, etc.).
    
    This uses the new observable-analyzer architecture.
    """
    internal_token = settings.INTERNAL_SERVICE_TOKEN
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{ANALYZER_ORCHESTRATOR_URL}/api/v1/analyze",
                json={
                    "tenant_id": current_tenant_id,
                    "observable_type": request.observable_type,
                    "observable_value": request.observable_value,
                    "metadata": request.metadata,
                    "analyzer_tags": request.analyzer_tags
                },
                headers={"Authorization": f"Bearer {internal_token}"}
            )
            response.raise_for_status()
            return response.json()
    
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Analyzer orchestrator error: {e.response.text}"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to analyzer orchestrator: {str(e)}"
        )


@router.get("/jobs/{job_id}")
async def get_analysis_job(
    job_id: str,
    current_tenant_id: str = Depends(get_current_tenant),
):
    """Get status of an analysis job."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{ANALYZER_ORCHESTRATOR_URL}/api/v1/jobs/{job_id}"
            )
            response.raise_for_status()
            return response.json()
    
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/analyzers")
async def list_analyzers(
    observable_type: Optional[str] = None,
    current_tenant_id: str = Depends(get_current_tenant),
):
    """List available analyzers."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {"observable_type": observable_type} if observable_type else {}
            response = await client.get(
                f"{ANALYZER_ORCHESTRATOR_URL}/api/v1/analyzers",
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/dashboard-snapshot")
async def get_posture_dashboard_snapshot(
    current_tenant_id: str = Depends(get_current_tenant),
):
    """
    Get cloud posture snapshot from the real orchestrator dashboard payload.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0, verify=settings.UPSTREAM_TLS_VERIFY) as client:
            response = await client.get(
                f"{settings.ORCHESTRATOR_URL}/api/v1/orchestrator/tenant/{current_tenant_id}/dashboard-snapshot",
                headers=build_trace_headers(
                    build_internal_auth_headers(
                        settings.INTERNAL_SERVICE_TOKEN,
                        tenant_id=current_tenant_id,
                    )
                ),
            )
            response.raise_for_status()
            payload = response.json() or {}
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Orchestrator dashboard snapshot error: {e.response.text}",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to orchestrator: {str(e)}",
        )

    cloud_posture = payload.get("cloud_posture")
    if not isinstance(cloud_posture, dict):
        raise HTTPException(
            status_code=503,
            detail="Cloud posture snapshot is unavailable from orchestrator",
        )

    return cloud_posture
