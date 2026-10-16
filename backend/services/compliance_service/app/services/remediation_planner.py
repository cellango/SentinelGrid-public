"""Remediation planner - creates detailed remediation plans for findings."""

import logging
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_

# Import from sg_core for shared models
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))
from sg_core.models import IAMFinding, PostureFinding

logger = logging.getLogger(__name__)


class RemediationPlanner:
    """Plans remediation actions for findings."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_remediation_plan(
        self,
        finding_id: UUID,
        finding_type: str,
        tenant_id: UUID,
        custom_steps: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a detailed remediation plan for a finding.
        
        Args:
            finding_id: Finding ID
            finding_type: 'iam_finding' or 'posture_finding'
            tenant_id: Tenant ID
            custom_steps: Optional custom remediation steps
            
        Returns:
            Remediation plan
        """
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
        
        # Use custom steps if provided, otherwise generate from finding
        if custom_steps:
            plan = {
                "steps": custom_steps,
                "estimated_time": self._estimate_time(custom_steps),
                "complexity": self._assess_complexity(custom_steps),
                "requires_approval": True
            }
        else:
            # Get existing remediation plan or generate new one
            if hasattr(finding, 'remediation_plan') and finding.remediation_plan:
                plan = finding.remediation_plan
            else:
                plan = {
                    "steps": [],
                    "estimated_time": "unknown",
                    "complexity": "medium",
                    "requires_approval": True
                }
        
        # Add metadata
        plan["finding_id"] = str(finding_id)
        plan["finding_type"] = finding_type
        plan["severity"] = finding.severity
        plan["created_at"] = finding.detected_at.isoformat() if hasattr(finding.detected_at, 'isoformat') else str(finding.detected_at)
        
        return plan
    
    def _estimate_time(self, steps: List[Dict[str, Any]]) -> str:
        """Estimate time required for remediation."""
        if not steps:
            return "unknown"
        
        # Simple estimation: 15 minutes per step
        estimated_minutes = len(steps) * 15
        
        if estimated_minutes < 60:
            return f"{estimated_minutes} minutes"
        else:
            hours = estimated_minutes // 60
            minutes = estimated_minutes % 60
            if minutes > 0:
                return f"{hours}h {minutes}m"
            return f"{hours} hours"
    
    def _assess_complexity(self, steps: List[Dict[str, Any]]) -> str:
        """Assess complexity of remediation."""
        if not steps:
            return "medium"
        
        # Check for playbook actions (automated = lower complexity)
        has_automation = any(step.get("playbook_action") for step in steps)
        
        if len(steps) <= 2 and has_automation:
            return "low"
        elif len(steps) <= 3:
            return "medium"
        else:
            return "high"

