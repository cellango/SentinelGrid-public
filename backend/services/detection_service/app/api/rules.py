"""Detection Rules API endpoints."""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_tenant_session
from app.core.security import get_current_tenant
from app.models.rule import DetectionRule
from app.engine.rule_engine import RuleEngine
from app.services.alert_service import create_alerts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rules", tags=["detection-rules"])


class RuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rule_type: str  # failed_logins, new_admin, suspicious_cloud
    pattern: dict  # Rule configuration
    severity: str = "medium"  # low, medium, high, critical
    enabled: bool = True


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    pattern: Optional[dict] = None
    severity: Optional[str] = None
    enabled: Optional[bool] = None


class RuleResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    rule_type: str
    pattern: dict
    enabled: bool
    severity: str
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    rule_data: RuleCreate,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Create a new detection rule."""
    # Validate rule type
    valid_types = ["failed_logins", "new_admin", "suspicious_cloud"]
    if rule_data.rule_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid rule type. Must be one of: {valid_types}"
        )
    
    # Validate severity
    valid_severities = ["low", "medium", "high", "critical"]
    if rule_data.severity not in valid_severities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid severity. Must be one of: {valid_severities}"
        )
    
    # Create rule
    rule = DetectionRule(
        tenant_id=UUID(tenant_id),
        name=rule_data.name,
        description=rule_data.description,
        rule_type=rule_data.rule_type,
        pattern=rule_data.pattern,
        severity=rule_data.severity,
        enabled=rule_data.enabled,
    )
    
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return RuleResponse(
        id=str(rule.id),
        tenant_id=str(rule.tenant_id),
        name=rule.name,
        description=rule.description,
        rule_type=rule.rule_type,
        pattern=rule.pattern,
        enabled=rule.enabled,
        severity=rule.severity,
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat(),
    )


@router.get("", response_model=List[RuleResponse])
def list_rules(
    tenant_id: str = Depends(get_current_tenant),
    enabled_only: bool = False,
    db: Session = Depends(get_tenant_session)
):
    """List all detection rules for the current tenant."""
    query = db.query(DetectionRule).filter(DetectionRule.tenant_id == UUID(tenant_id))
    
    if enabled_only:
        query = query.filter(DetectionRule.enabled == True)
    
    rules = query.all()
    
    return [
        RuleResponse(
            id=str(r.id),
            tenant_id=str(r.tenant_id),
            name=r.name,
            description=r.description,
            rule_type=r.rule_type,
            pattern=r.pattern,
            enabled=r.enabled,
            severity=r.severity,
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
        )
        for r in rules
    ]


@router.get("/{rule_id}", response_model=RuleResponse)
def get_rule(
    rule_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Get a specific detection rule."""
    rule = db.query(DetectionRule).filter(
        DetectionRule.id == UUID(rule_id),
        DetectionRule.tenant_id == UUID(tenant_id)
    ).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    
    return RuleResponse(
        id=str(rule.id),
        tenant_id=str(rule.tenant_id),
        name=rule.name,
        description=rule.description,
        rule_type=rule.rule_type,
        pattern=rule.pattern,
        enabled=rule.enabled,
        severity=rule.severity,
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat(),
    )


@router.patch("/{rule_id}", response_model=RuleResponse)
def update_rule(
    rule_id: str,
    rule_data: RuleUpdate,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Update a detection rule."""
    rule = db.query(DetectionRule).filter(
        DetectionRule.id == UUID(rule_id),
        DetectionRule.tenant_id == UUID(tenant_id)
    ).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    
    if rule_data.name is not None:
        rule.name = rule_data.name
    if rule_data.description is not None:
        rule.description = rule_data.description
    if rule_data.pattern is not None:
        rule.pattern = rule_data.pattern
    if rule_data.severity is not None:
        if rule_data.severity not in ["low", "medium", "high", "critical"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid severity"
            )
        rule.severity = rule_data.severity
    if rule_data.enabled is not None:
        rule.enabled = rule_data.enabled
    
    db.commit()
    db.refresh(rule)
    
    return RuleResponse(
        id=str(rule.id),
        tenant_id=str(rule.tenant_id),
        name=rule.name,
        description=rule.description,
        rule_type=rule.rule_type,
        pattern=rule.pattern,
        enabled=rule.enabled,
        severity=rule.severity,
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat(),
    )


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    rule_id: str,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """Delete a detection rule."""
    rule = db.query(DetectionRule).filter(
        DetectionRule.id == UUID(rule_id),
        DetectionRule.tenant_id == UUID(tenant_id)
    ).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    
    db.delete(rule)
    db.commit()


@router.post("/{rule_id}/evaluate", status_code=status.HTTP_200_OK)
async def evaluate_rule(
    rule_id: str,
    tenant_id: str = Depends(get_current_tenant),
    create_alerts_flag: bool = True,
    db: Session = Depends(get_tenant_session)
):
    """Manually trigger evaluation of a rule."""
    rule = db.query(DetectionRule).filter(
        DetectionRule.id == UUID(rule_id),
        DetectionRule.tenant_id == UUID(tenant_id)
    ).first()
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    
    # Evaluate rule
    engine = RuleEngine(db)
    alerts = await engine.evaluate_rule(rule)
    
    # Create alerts if requested
    if create_alerts_flag and alerts:
        await create_alerts(tenant_id, alerts)
    
    return {
        "rule_id": str(rule.id),
        "rule_name": rule.name,
        "alerts_generated": len(alerts),
        "alerts": alerts,
    }


@router.post("/evaluate/all", status_code=status.HTTP_200_OK)
async def evaluate_all_rules(
    tenant_id: str = Depends(get_current_tenant),
    create_alerts_flag: bool = True,
    db: Session = Depends(get_tenant_session)
):
    """Evaluate all enabled rules for the current tenant."""
    engine = RuleEngine(db)
    results = await engine.evaluate_all_rules(tenant_id)
    
    # Create alerts if requested
    if create_alerts_flag:
        all_alerts = []
        for rule_result in results["rule_results"]:
            all_alerts.extend(rule_result.get("alerts", []))
        
        if all_alerts:
            await create_alerts(tenant_id, all_alerts)
    
    return results


class EnableRulesRequest(BaseModel):
    tenant_id: str
    rule_keys: list[str]  # ["failed_logins", "new_admin", "suspicious_cloud"]


class EnableRulesResponse(BaseModel):
    tenant_id: str
    rules_enabled: list[str]
    rules_created: int
    rules_updated: int


@router.post("/enable", response_model=EnableRulesResponse, status_code=status.HTTP_200_OK)
def enable_baseline_rules(
    request: EnableRulesRequest,
    tenant_id: str = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session)
):
    """
    Enable baseline detection rules for a tenant.
    
    Creates or enables the specified baseline rules. Used during onboarding.
    """
    valid_rule_keys = ["failed_logins", "new_admin", "suspicious_cloud"]
    if request.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-tenant access denied",
        )
    
    # Validate rule keys
    invalid_keys = [key for key in request.rule_keys if key not in valid_rule_keys]
    if invalid_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid rule keys: {invalid_keys}. Valid keys: {valid_rule_keys}"
        )
    
    tenant_uuid = UUID(request.tenant_id)
    rules_enabled = []
    rules_created = 0
    rules_updated = 0
    
    # Baseline rule configurations
    baseline_rules = {
        "failed_logins": {
            "name": "Multiple Failed Logins",
            "description": "Alert when 5+ failed logins occur in 15 minutes",
            "pattern": {
                "event_type": "login.failure",
                "time_window_minutes": 15,
                "threshold": 5
            },
            "severity": "high"
        },
        "new_admin": {
            "name": "New Admin User",
            "description": "Alert when a new admin account is created",
            "pattern": {
                "event_type": "user.created",
                "user_role": "admin"
            },
            "severity": "medium"
        },
        "suspicious_cloud": {
            "name": "Suspicious Cloud Actions",
            "description": "Alert on unusual AWS/Azure/GCP API calls",
            "pattern": {
                "event_type": "cloud.api_call",
                "suspicious_actions": [
                    "DeleteBucket",
                    "TerminateInstance",
                    "DeleteSecurityGroup"
                ]
            },
            "severity": "high"
        }
    }
    
    for rule_key in request.rule_keys:
        rule_config = baseline_rules[rule_key]
        
        # Check if rule already exists
        existing_rule = db.query(DetectionRule).filter(
            DetectionRule.tenant_id == tenant_uuid,
            DetectionRule.rule_type == rule_key
        ).first()
        
        if existing_rule:
            # Update existing rule to enabled
            if not existing_rule.enabled:
                existing_rule.enabled = True
                rules_updated += 1
            rules_enabled.append(rule_key)
        else:
            # Create new rule
            new_rule = DetectionRule(
                tenant_id=tenant_uuid,
                name=rule_config["name"],
                description=rule_config["description"],
                rule_type=rule_key,
                pattern=rule_config["pattern"],
                severity=rule_config["severity"],
                enabled=True
            )
            db.add(new_rule)
            rules_created += 1
            rules_enabled.append(rule_key)
    
    db.commit()
    
    logger.info(f"Enabled {len(rules_enabled)} baseline rules for tenant {request.tenant_id}")
    
    return EnableRulesResponse(
        tenant_id=request.tenant_id,
        rules_enabled=rules_enabled,
        rules_created=rules_created,
        rules_updated=rules_updated
    )
