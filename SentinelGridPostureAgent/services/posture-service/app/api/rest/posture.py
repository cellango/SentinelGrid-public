"""Posture summary and metrics API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..')))

from shared.database import get_db
from shared.models.finding import Finding, FindingSeverity, FindingStatus
from shared.models.asset import Asset
from sqlalchemy import func, and_
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/posture", tags=["posture"])


class PostureSummaryResponse(BaseModel):
    """Posture summary response."""
    tenant_id: str
    posture_score: float
    grade: str
    total_findings: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    info_findings: int
    findings_by_source: dict
    total_assets: int


@router.get("/summary/{tenant_id}", response_model=PostureSummaryResponse)
async def get_posture_summary(
    tenant_id: str,
    db: Session = Depends(get_db)
):
    """
    Get overall posture summary with score and risk counts.
    
    Args:
        tenant_id: Tenant identifier
        db: Database session
    
    Returns:
        Posture summary with scores and counts
    """
    logger.info(f"Getting posture summary for tenant: {tenant_id}")
    
    # Get findings counts by severity
    findings_by_severity = (
        db.query(
            Finding.severity,
            func.count(Finding.id).label("count")
        )
        .filter(and_(
            Finding.tenant_id == tenant_id,
            Finding.status == FindingStatus.OPEN
        ))
        .group_by(Finding.severity)
        .all()
    )
    
    severity_counts = {severity.value: 0 for severity in FindingSeverity}
    for severity, count in findings_by_severity:
        severity_counts[severity.value] = count
    
    total_findings = sum(severity_counts.values())
    
    # Get findings by source
    findings_by_source = (
        db.query(
            Finding.source,
            func.count(Finding.id).label("count")
        )
        .filter(and_(
            Finding.tenant_id == tenant_id,
            Finding.status == FindingStatus.OPEN
        ))
        .group_by(Finding.source)
        .all()
    )
    
    source_breakdown = {source.value: count for source, count in findings_by_source}
    
    # Get total assets
    total_assets = (
        db.query(func.count(Asset.id))
        .filter(Asset.tenant_id == tenant_id)
        .scalar()
    ) or 0
    
    # Calculate posture score (0-100)
    # Simple formula: Start at 100, deduct points for findings
    # Critical = -10, High = -5, Medium = -2, Low = -1, Info = -0.5
    score = 100.0
    score -= severity_counts.get("critical", 0) * 10
    score -= severity_counts.get("high", 0) * 5
    score -= severity_counts.get("medium", 0) * 2
    score -= severity_counts.get("low", 0) * 1
    score -= severity_counts.get("info", 0) * 0.5
    score = max(0.0, min(100.0, score))  # Clamp to 0-100
    
    # Calculate grade
    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"
    else:
        grade = "F"
    
    return PostureSummaryResponse(
        tenant_id=tenant_id,
        posture_score=round(score, 2),
        grade=grade,
        total_findings=total_findings,
        critical_findings=severity_counts.get("critical", 0),
        high_findings=severity_counts.get("high", 0),
        medium_findings=severity_counts.get("medium", 0),
        low_findings=severity_counts.get("low", 0),
        info_findings=severity_counts.get("info", 0),
        findings_by_source=source_breakdown,
        total_assets=total_assets
    )


@router.get("/trends/{tenant_id}")
async def get_posture_trends(
    tenant_id: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get posture trends over time.
    
    Args:
        tenant_id: Tenant identifier
        days: Number of days to look back
        db: Database session
    
    Returns:
        Posture trends data
    """
    # TODO: Implement trends calculation from posture_scores table
    return {
        "tenant_id": tenant_id,
        "days": days,
        "trends": [],
        "message": "Trends calculation not yet implemented"
    }


@router.get("/top-risks/{tenant_id}")
async def get_top_risks(
    tenant_id: str,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get top N critical findings.
    
    Args:
        tenant_id: Tenant identifier
        limit: Number of findings to return
        db: Database session
    
    Returns:
        List of top risk findings
    """
    # Get critical and high severity findings
    top_findings = (
        db.query(Finding)
        .filter(and_(
            Finding.tenant_id == tenant_id,
            Finding.status == FindingStatus.OPEN,
            Finding.severity.in_([FindingSeverity.CRITICAL, FindingSeverity.HIGH])
        ))
        .order_by(Finding.severity.desc(), Finding.first_seen_at.asc())
        .limit(limit)
        .all()
    )
    
    return {
        "tenant_id": tenant_id,
        "top_risks": [
            {
                "id": str(f.id),
                "title": f.title,
                "severity": f.severity.value,
                "source": f.source.value,
                "tool": f.tool,
                "asset_id": str(f.asset_id) if f.asset_id else None,
                "first_seen": f.first_seen_at.isoformat() if f.first_seen_at else None
            }
            for f in top_findings
        ],
        "count": len(top_findings)
    }

