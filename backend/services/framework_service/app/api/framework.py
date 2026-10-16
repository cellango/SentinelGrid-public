"""API endpoints for framework mapping."""

import logging
from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from app.core.database import get_current_tenant, get_tenant_session
from app.services.framework_mapper import FrameworkMapper
from app.services.soc2_mapper import SOC2Mapper

logger = logging.getLogger(__name__)

router = APIRouter()
framework_mapper = FrameworkMapper()
soc2_mapper = SOC2Mapper()


class MapRequest(BaseModel):
    """Framework mapping request."""
    ticket_data: Optional[Dict[str, Any]] = None
    tenant_id: Optional[UUID] = None

    model_config = ConfigDict(extra="allow")


class FindingMapRequest(BaseModel):
    """Finding-to-framework mapping request."""
    finding_type: str
    finding_identifier: Optional[str] = None
    category: Optional[str] = None
    severity: str = "medium"
    tenant_id: Optional[UUID] = None

    model_config = ConfigDict(extra="allow")


def _enforce_same_tenant(request_tenant_id: Optional[UUID], current_tenant: str) -> str:
    if request_tenant_id and str(request_tenant_id) != str(current_tenant):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access denied",
        )
    return current_tenant


def _map_request_ticket_data(request: MapRequest) -> Dict[str, Any]:
    if request.ticket_data is not None:
        return request.ticket_data
    extras = dict(request.model_extra or {})
    extras.pop("tenant_id", None)
    return extras


def _finding_request_ticket_data(request: FindingMapRequest) -> Dict[str, Any]:
    data = dict(request.model_extra or {})
    identifier = request.finding_identifier or request.category or request.finding_type
    data.update(
        {
            "category": identifier,
            "severity": request.severity,
            "finding_type": request.finding_type,
        }
    )
    return data


@router.post("/map")
async def map_to_frameworks(
    request: MapRequest,
    current_tenant: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """
    Map incident/ticket to NIST and MITRE frameworks.
    
    Args:
        request: Mapping request with ticket data
        db: Database session
    
    Returns:
        Framework mappings
    """
    try:
        tenant_id = _enforce_same_tenant(request.tenant_id, current_tenant)
        ticket_data = _map_request_ticket_data(request)
        ticket_data.setdefault("tenant_id", tenant_id)
        mappings = await framework_mapper.map_incident(ticket_data)
        return mappings
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Error mapping to frameworks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/map/nist")
async def map_to_nist_controls(
    request: MapRequest,
    current_tenant: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Map incident/ticket data to NIST controls."""
    del db
    tenant_id = _enforce_same_tenant(request.tenant_id, current_tenant)
    ticket_data = _map_request_ticket_data(request)
    ticket_data.setdefault("tenant_id", tenant_id)
    controls = await framework_mapper.nist_mapper.map_incident_to_controls(ticket_data)
    return {"controls": controls, "nist_controls": controls}


@router.post("/map/mitre")
async def map_to_mitre(
    request: MapRequest,
    current_tenant: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Map incident/ticket data to MITRE ATT&CK."""
    del db
    tenant_id = _enforce_same_tenant(request.tenant_id, current_tenant)
    ticket_data = _map_request_ticket_data(request)
    ticket_data.setdefault("tenant_id", tenant_id)
    mapping = await framework_mapper.mitre_mapper.map_incident_to_mitre(ticket_data)
    return {
        "tactics": mapping.get("tactics", []),
        "techniques": mapping.get("techniques", []),
        "mitre_tactics": mapping.get("tactics", []),
        "mitre_techniques": mapping.get("techniques", []),
    }


@router.post("/map-to-nist")
async def map_finding_to_nist(
    request: FindingMapRequest,
    current_tenant: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Map a finding identifier to a primary NIST control."""
    del db
    tenant_id = _enforce_same_tenant(request.tenant_id, current_tenant)
    ticket_data = _finding_request_ticket_data(request)
    ticket_data.setdefault("tenant_id", tenant_id)
    controls = await framework_mapper.nist_mapper.map_incident_to_controls(ticket_data)
    primary = controls[0] if controls else None
    return {
        "nist_control_id": primary.get("control_id") if primary else None,
        "controls": controls,
        "nist_controls": controls,
    }


@router.post("/map-to-soc2")
async def map_finding_to_soc2(
    request: FindingMapRequest,
    current_tenant: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Map a finding identifier to SOC 2 criteria."""
    del db
    tenant_id = _enforce_same_tenant(request.tenant_id, current_tenant)
    ticket_data = _finding_request_ticket_data(request)
    ticket_data.setdefault("tenant_id", tenant_id)
    criteria = await framework_mapper.soc2_mapper.map_incident_to_criteria(ticket_data)
    return {"soc2_criteria": criteria}


@router.get("/nist/{control_id}")
async def get_nist_control(
    control_id: str,
    current_tenant: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Get NIST control details."""
    del current_tenant, db
    # Placeholder - would fetch from knowledge base
    return {
        "control_id": control_id,
        "title": "NIST Control",
        "description": "Control description"
    }


@router.get("/mitre/{technique_id}")
async def get_mitre_technique(
    technique_id: str,
    current_tenant: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Get MITRE technique details."""
    del current_tenant, db
    # Placeholder - would fetch from knowledge base
    return {
        "technique_id": technique_id,
        "name": "MITRE Technique",
        "description": "Technique description"
    }


@router.get("/soc2/{criterion_id}")
async def get_soc2_criterion(
    criterion_id: str,
    current_tenant: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Get SOC 2 criterion details."""
    del current_tenant, db
    crit = soc2_mapper.get_criterion(criterion_id)
    if not crit:
        raise HTTPException(status_code=404, detail="Criterion not found")
    return crit
