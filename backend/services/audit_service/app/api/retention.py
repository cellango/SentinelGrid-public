"""Audit retention policy API endpoints."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_current_tenant, get_tenant_session

logger = logging.getLogger(__name__)

router = APIRouter()


def _enforce_same_tenant(requested_tenant_id: UUID, current_tenant_id: UUID) -> None:
    if requested_tenant_id != current_tenant_id:
        raise HTTPException(
            status_code=403,
            detail="Tenant ID mismatch. You can only access your own tenant's data.",
        )


class RetentionPolicyCreate(BaseModel):
    """Retention policy creation model."""
    policy_name: str
    hot_retention_days: int = 90
    cold_retention_days: int = 365
    total_retention_days: int = 2555  # 7 years for SOC 2
    archive_enabled: bool = False
    archive_location: Optional[str] = None
    requires_immutability: bool = True
    requires_encryption: bool = True


class RetentionPolicyUpdate(BaseModel):
    """Retention policy update model."""
    hot_retention_days: Optional[int] = None
    cold_retention_days: Optional[int] = None
    total_retention_days: Optional[int] = None
    archive_enabled: Optional[bool] = None
    archive_location: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/policies")
async def get_retention_policies(
    tenant_id: UUID,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Get retention policies for a tenant."""
    _enforce_same_tenant(tenant_id, current_tenant_id)
    query = text("""
        SELECT id, tenant_id, policy_name, hot_retention_days, cold_retention_days,
               total_retention_days, archive_enabled, archive_location,
               requires_immutability, requires_encryption, is_active,
               created_at, updated_at
        FROM audit_retention_policies
        WHERE tenant_id = :tenant_id OR tenant_id IS NULL
        ORDER BY created_at DESC
    """)
    
    result = db.execute(query, {"tenant_id": str(tenant_id)})
    policies = result.fetchall()
    
    policies_list = []
    for policy in policies:
        policies_list.append({
            "id": str(policy[0]),
            "tenant_id": str(policy[1]) if policy[1] else None,
            "policy_name": policy[2],
            "hot_retention_days": policy[3],
            "cold_retention_days": policy[4],
            "total_retention_days": policy[5],
            "archive_enabled": policy[6],
            "archive_location": policy[7],
            "requires_immutability": policy[8],
            "requires_encryption": policy[9],
            "is_active": policy[10],
            "created_at": policy[11].isoformat() if policy[11] else None,
            "updated_at": policy[12].isoformat() if policy[12] else None
        })
    
    return {"policies": policies_list}


@router.post("/policies")
async def create_retention_policy(
    tenant_id: UUID,
    policy: RetentionPolicyCreate,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Create a new retention policy for a tenant."""
    _enforce_same_tenant(tenant_id, current_tenant_id)
    query = text("""
        INSERT INTO audit_retention_policies (
            tenant_id, policy_name, hot_retention_days, cold_retention_days,
            total_retention_days, archive_enabled, archive_location,
            requires_immutability, requires_encryption
        ) VALUES (
            :tenant_id, :policy_name, :hot_retention_days, :cold_retention_days,
            :total_retention_days, :archive_enabled, :archive_location,
            :requires_immutability, :requires_encryption
        )
        RETURNING id
    """)
    
    try:
        result = db.execute(query, {
            "tenant_id": str(tenant_id),
            "policy_name": policy.policy_name,
            "hot_retention_days": policy.hot_retention_days,
            "cold_retention_days": policy.cold_retention_days,
            "total_retention_days": policy.total_retention_days,
            "archive_enabled": policy.archive_enabled,
            "archive_location": policy.archive_location,
            "requires_immutability": policy.requires_immutability,
            "requires_encryption": policy.requires_encryption
        })
        
        db.commit()
        policy_id = result.fetchone()[0]
        
        return {
            "id": str(policy_id),
            "message": "Retention policy created successfully"
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create retention policy: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/policies/{policy_id}")
async def update_retention_policy(
    policy_id: UUID,
    tenant_id: UUID,
    policy: RetentionPolicyUpdate,
    current_tenant_id: UUID = Depends(get_current_tenant),
    db: Session = Depends(get_tenant_session),
):
    """Update a retention policy."""
    _enforce_same_tenant(tenant_id, current_tenant_id)
    # Build update query dynamically based on provided fields
    updates = []
    params = {"policy_id": str(policy_id), "tenant_id": str(tenant_id)}
    
    if policy.hot_retention_days is not None:
        updates.append("hot_retention_days = :hot_retention_days")
        params["hot_retention_days"] = policy.hot_retention_days
    
    if policy.cold_retention_days is not None:
        updates.append("cold_retention_days = :cold_retention_days")
        params["cold_retention_days"] = policy.cold_retention_days
    
    if policy.total_retention_days is not None:
        updates.append("total_retention_days = :total_retention_days")
        params["total_retention_days"] = policy.total_retention_days
    
    if policy.archive_enabled is not None:
        updates.append("archive_enabled = :archive_enabled")
        params["archive_enabled"] = policy.archive_enabled
    
    if policy.archive_location is not None:
        updates.append("archive_location = :archive_location")
        params["archive_location"] = policy.archive_location
    
    if policy.is_active is not None:
        updates.append("is_active = :is_active")
        params["is_active"] = policy.is_active
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append("updated_at = NOW()")
    
    query = text(f"""
        UPDATE audit_retention_policies
        SET {', '.join(updates)}
        WHERE id = :policy_id AND tenant_id = :tenant_id
        RETURNING id
    """)
    
    result = db.execute(query, params)
    db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    return {"message": "Retention policy updated successfully"}
