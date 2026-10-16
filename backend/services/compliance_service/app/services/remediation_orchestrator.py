"""Remediation orchestrator - executes remediation via playbooks."""

import logging
import httpx
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

# Import from sg_core for shared models
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))
from sg_core.models import IAMFinding, PostureFinding, RemediationMetadata
from app.core.config import settings

logger = logging.getLogger(__name__)


class RemediationOrchestrator:
    """Orchestrates remediation execution via playbooks."""
    
    def __init__(self, db: Session):
        self.db = db
        self.soar_agent_url = settings.SOAR_AGENT_URL
    
    async def execute_remediation(
        self,
        finding_id: UUID,
        finding_type: str,
        tenant_id: UUID,
        playbook_id: Optional[UUID] = None,
        auto_approve: bool = False
    ) -> Dict[str, Any]:
        """
        Execute remediation for a finding via playbook.
        
        Args:
            finding_id: Finding ID
            finding_type: 'iam_finding' or 'posture_finding'
            tenant_id: Tenant ID
            playbook_id: Optional specific playbook ID (otherwise uses plan's playbook)
            auto_approve: Whether to auto-approve playbook execution
            
        Returns:
            Execution result
        """
        # Get finding
        if finding_type == "iam_finding":
            finding = self.db.query(IAMFinding).filter(
                and_(IAMFinding.id == finding_id, IAMFinding.tenant_id == tenant_id)
            ).first()
        elif finding_type == "posture_finding":
            finding = self.db.query(PostureFinding).filter(
                and_(PostureFinding.id == finding_id, PostureFinding.tenant_id == tenant_id)
            ).first()
        else:
            raise ValueError(f"Invalid finding type: {finding_type}")
        
        if not finding:
            raise ValueError(f"Finding {finding_id} not found for tenant {tenant_id}")
        
        # Get remediation plan
        remediation_plan = finding.remediation_plan if hasattr(finding, 'remediation_plan') and finding.remediation_plan else {}
        
        # Determine playbook to use
        if not playbook_id:
            # Try to get playbook from remediation plan
            playbook_id = remediation_plan.get("playbook_id")
            if playbook_id:
                playbook_id = UUID(playbook_id)
        
        if not playbook_id:
            raise ValueError("No playbook specified for remediation")
        
        # Create remediation metadata record
        remediation_metadata = RemediationMetadata(
            id=uuid4(),
            tenant_id=tenant_id,
            finding_id=finding_id,
            finding_type=finding_type,
            remediation_plan=remediation_plan,
            status="pending"
        )
        self.db.add(remediation_metadata)
        
        try:
            # Update finding status
            finding.remediation_status = "in_progress"
            self.db.commit()
            
            # Trigger playbook via SOAR Agent
            execution_result = await self._execute_playbook_via_soar(
                playbook_id=playbook_id,
                finding_id=finding_id,
                finding_type=finding_type,
                tenant_id=tenant_id,
                remediation_plan=remediation_plan,
                auto_approve=auto_approve
            )
            
            # Update remediation metadata with execution ID
            if execution_result.get("execution_id"):
                remediation_metadata.playbook_execution_id = UUID(execution_result["execution_id"])
                remediation_metadata.status = "in_progress"
            
            self.db.commit()
            
            logger.info(
                f"Started remediation for {finding_type} {finding_id}. "
                f"Execution ID: {execution_result.get('execution_id')}"
            )
            
            return {
                "remediation_id": str(remediation_metadata.id),
                "execution_id": execution_result.get("execution_id"),
                "status": "in_progress",
                "finding_id": str(finding_id),
                "finding_type": finding_type
            }
        
        except Exception as e:
            self.db.rollback()
            finding.remediation_status = "failed"
            remediation_metadata.status = "failed"
            self.db.commit()
            
            logger.error(f"Failed to execute remediation for {finding_type} {finding_id}: {e}", exc_info=True)
            raise
    
    async def _execute_playbook_via_soar(
        self,
        playbook_id: UUID,
        finding_id: UUID,
        finding_type: str,
        tenant_id: UUID,
        remediation_plan: Dict[str, Any],
        auto_approve: bool = False
    ) -> Dict[str, Any]:
        """
        Execute playbook via SOAR Agent.
        
        Args:
            playbook_id: Playbook ID
            finding_id: Finding ID
            finding_type: Finding type
            tenant_id: Tenant ID
            remediation_plan: Remediation plan
            auto_approve: Whether to auto-approve
            
        Returns:
            Execution result from SOAR Agent
        """
        url = f"{self.soar_agent_url}/internal/soar/playbooks/{playbook_id}/execute"
        
        payload = {
            "tenant_id": str(tenant_id),
            "target_type": finding_type,
            "target_id": str(finding_id),
            "triggered_by": "compliance_service",
            "auto_approve": auto_approve,
            "params": {
                "finding_id": str(finding_id),
                "finding_type": finding_type,
                "remediation_plan": remediation_plan,
                "trigger_source": "compliance_service"
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Tenant-ID": str(tenant_id)
        }
        
        if settings.INTERNAL_SERVICE_TOKEN:
            headers["Authorization"] = f"Bearer {settings.INTERNAL_SERVICE_TOKEN}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"SOAR Agent returned error: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Error calling SOAR Agent: {e}", exc_info=True)
                raise
    
    def update_remediation_status(
        self,
        remediation_id: UUID,
        status: str,
        tenant_id: UUID,
        execution_id: Optional[UUID] = None
    ) -> None:
        """
        Update remediation status.
        
        Args:
            remediation_id: Remediation metadata ID
            status: New status ('pending', 'in_progress', 'completed', 'failed')
            tenant_id: Tenant ID
            execution_id: Optional playbook execution ID
        """
        remediation = self.db.query(RemediationMetadata).filter(
            and_(
                RemediationMetadata.id == remediation_id,
                RemediationMetadata.tenant_id == tenant_id
            )
        ).first()
        
        if not remediation:
            raise ValueError(f"Remediation {remediation_id} not found")
        
        remediation.status = status
        if execution_id:
            remediation.playbook_execution_id = execution_id
        
        # Update finding status
        if remediation.finding_type == "iam_finding":
            finding = self.db.query(IAMFinding).filter(
                IAMFinding.id == remediation.finding_id
            ).first()
        else:
            finding = self.db.query(PostureFinding).filter(
                PostureFinding.id == remediation.finding_id
            ).first()
        
        if finding:
            finding.remediation_status = status
            if status == "completed":
                finding.remediated_at = datetime.utcnow()
        
        self.db.commit()
        logger.info(f"Updated remediation {remediation_id} status to {status}")

