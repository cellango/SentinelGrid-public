"""Findings API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..')))

from shared.database import get_db
from shared.models.finding import Finding, FindingSeverity, FindingStatus, FindingSource
from sqlalchemy import and_, or_
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/findings", tags=["findings"])


class BulkCreateFindingsRequest(BaseModel):
    """Request to bulk create findings."""
    tenant_id: str
    findings: List[dict]
    job_id: Optional[str] = None


class UpdateFindingRequest(BaseModel):
    """Request to update a finding."""
    status: Optional[str] = None
    resolved_by: Optional[str] = None


@router.get("/")
async def list_findings(
    tenant_id: str = Query(...),
    severity: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    tool: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """
    List findings with filters.
    
    Args:
        tenant_id: Tenant identifier
        severity: Filter by severity
        source: Filter by source (cspm, iac, dast, etc.)
        tool: Filter by tool (prowler, zap, etc.)
        status: Filter by status
        limit: Max results
        offset: Pagination offset
        db: Database session
    
    Returns:
        List of findings
    """
    logger.info(f"Listing findings for tenant: {tenant_id}")
    
    # Build query
    query = db.query(Finding).filter(Finding.tenant_id == tenant_id)
    
    if severity:
        try:
            severity_enum = FindingSeverity(severity)
            query = query.filter(Finding.severity == severity_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")
    
    if source:
        try:
            source_enum = FindingSource(source)
            query = query.filter(Finding.source == source_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid source: {source}")
    
    if tool:
        query = query.filter(Finding.tool == tool)
    
    if status:
        try:
            status_enum = FindingStatus(status)
            query = query.filter(Finding.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    # Order by severity (critical first) and date
    query = query.order_by(Finding.severity.desc(), Finding.first_seen_at.desc())
    
    # Pagination
    total_count = query.count()
    findings = query.offset(offset).limit(limit).all()
    
    return {
        "findings": [
            {
                "id": str(f.id),
                "tenant_id": str(f.tenant_id),
                "asset_id": str(f.asset_id) if f.asset_id else None,
                "title": f.title,
                "description": f.description,
                "severity": f.severity.value,
                "status": f.status.value,
                "source": f.source.value,
                "tool": f.tool,
                "observable_type": f.observable_type,
                "observable_value": f.observable_value,
                "first_seen_at": f.first_seen_at.isoformat() if f.first_seen_at else None,
                "last_seen_at": f.last_seen_at.isoformat() if f.last_seen_at else None
            }
            for f in findings
        ],
        "total_count": total_count,
        "limit": limit,
        "offset": offset
    }


@router.get("/{finding_id}")
async def get_finding(
    finding_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed finding information.
    
    Args:
        finding_id: Finding identifier
        db: Database session
    
    Returns:
        Finding details
    """
    try:
        finding_uuid = uuid.UUID(finding_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid finding ID format")
    
    finding = db.query(Finding).filter(Finding.id == finding_uuid).first()
    
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    
    return {
        "id": str(finding.id),
        "tenant_id": str(finding.tenant_id),
        "asset_id": str(finding.asset_id) if finding.asset_id else None,
        "finding_id": finding.finding_id,
        "source": finding.source.value,
        "tool": finding.tool,
        "check_id": finding.check_id,
        "control_id": finding.control_id,
        "title": finding.title,
        "description": finding.description,
        "severity": finding.severity.value,
        "status": finding.status.value,
        "framework_refs": finding.framework_refs,
        "evidence": finding.evidence,
        "remediation": finding.remediation,
        "observable_type": finding.observable_type,
        "observable_value": finding.observable_value,
        "first_seen_at": finding.first_seen_at.isoformat() if finding.first_seen_at else None,
        "last_seen_at": finding.last_seen_at.isoformat() if finding.last_seen_at else None,
        "resolved_at": finding.resolved_at.isoformat() if finding.resolved_at else None,
        "resolved_by": str(finding.resolved_by) if finding.resolved_by else None
    }


@router.patch("/{finding_id}")
async def update_finding(
    finding_id: str,
    request: UpdateFindingRequest,
    db: Session = Depends(get_db)
):
    """
    Update a finding (status, resolution).
    
    Args:
        finding_id: Finding identifier
        request: Update request
        db: Database session
    
    Returns:
        Updated finding
    """
    try:
        finding_uuid = uuid.UUID(finding_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid finding ID format")
    
    finding = db.query(Finding).filter(Finding.id == finding_uuid).first()
    
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    
    # Update fields
    if request.status:
        try:
            finding.status = FindingStatus(request.status)
            if request.status in ["fixed", "false_positive"]:
                finding.resolved_at = datetime.utcnow()
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {request.status}")
    
    if request.resolved_by:
        try:
            finding.resolved_by = uuid.UUID(request.resolved_by)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid resolved_by UUID")
    
    db.commit()
    db.refresh(finding)
    
    logger.info(f"Updated finding {finding_id}: status={finding.status.value}")
    
    return {"id": str(finding.id), "status": finding.status.value, "message": "Finding updated"}


@router.post("/bulk")
async def bulk_create_findings(
    request: BulkCreateFindingsRequest,
    db: Session = Depends(get_db)
):
    """
    Bulk create findings (used by analyzer orchestrator).
    
    Args:
        request: Bulk create request with findings list
        db: Database session
    
    Returns:
        Count of findings created/updated
    """
    logger.info(f"Bulk creating {len(request.findings)} findings for tenant {request.tenant_id}")
    
    created_count = 0
    updated_count = 0
    
    for finding_data in request.findings:
        try:
            # Generate a unique finding_id based on tool + check_id + observable
            finding_id = f"{finding_data['tool']}_{finding_data.get('check_id', 'unknown')}_{finding_data['observable_value']}"
            
            # Check if finding already exists
            existing = (
                db.query(Finding)
                .filter(and_(
                    Finding.tenant_id == request.tenant_id,
                    Finding.source == finding_data["source"],
                    Finding.tool == finding_data["tool"],
                    Finding.finding_id == finding_id
                ))
                .first()
            )
            
            if existing:
                # Update last_seen_at
                existing.last_seen_at = datetime.utcnow()
                updated_count += 1
            else:
                # Create new finding
                finding = Finding(
                    tenant_id=uuid.UUID(request.tenant_id),
                    finding_id=finding_id,
                    source=FindingSource(finding_data["source"]),
                    tool=finding_data["tool"],
                    check_id=finding_data.get("check_id"),
                    title=finding_data["title"],
                    description=finding_data.get("description"),
                    severity=FindingSeverity(finding_data["severity"]),
                    status=FindingStatus.OPEN,
                    framework_refs=finding_data.get("framework_refs"),
                    evidence=finding_data.get("evidence"),
                    remediation=finding_data.get("remediation"),
                    observable_type=finding_data.get("observable_type"),
                    observable_value=finding_data.get("observable_value")
                )
                db.add(finding)
                created_count += 1
        
        except Exception as e:
            logger.error(f"Error creating finding: {str(e)}")
            continue
    
    db.commit()
    
    logger.info(f"Bulk create complete: {created_count} created, {updated_count} updated")
    
    return {
        "created": created_count,
        "updated": updated_count,
        "total": len(request.findings),
        "job_id": request.job_id
    }

