"""
Workflow Integration Service
Legacy workflow compatibility; unqualified provider access is blocked.
"""

from app.services.itdr_service import block_legacy_response

import logging
from typing import List, Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class WorkflowIntegrationService:
    """Service for integrating with SOAR and workflow engines."""
    
    def __init__(self):
        self.soar_url = getattr(settings, 'SOAR_SERVICE_URL', 'http://soar_agent:8000')
        self.workflow_engine_url = getattr(settings, 'WORKFLOW_ENGINE_URL', 'http://workflow_engine:8000')
    
    def trigger_soar_playbook(
        self,
        playbook_id: str,
        incident_data: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    def create_automated_approval_workflow(
        self,
        request_type: str,
        request_data: Dict[str, Any],
        approval_rules: List[Dict[str, Any]],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    def execute_remediation_workflow(
        self,
        violation_type: str,
        violation_data: Dict[str, Any],
        remediation_steps: List[str],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    def get_workflow_status(
        self,
        workflow_execution_id: str
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    def create_risk_response_playbook(
        self,
        risk_level: str,
        user_id: str,
        risk_details: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()
    
    def _build_approval_steps(
        self,
        approval_rules: List[Dict[str, Any]],
        request_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build approval workflow steps from rules."""
        steps = []
        
        for rule in approval_rules:
            rule_type = rule.get("type")
            
            if rule_type == "risk_based":
                # Auto-approve if risk below threshold
                threshold = rule.get("threshold", 50)
                risk_score = request_data.get("risk_score", 0)
                
                if risk_score < threshold:
                    steps.append({
                        "type": "auto_approve",
                        "condition": f"risk_score < {threshold}",
                        "action": "approve"
                    })
                else:
                    steps.append({
                        "type": "manual_approval",
                        "condition": f"risk_score >= {threshold}",
                        "approvers": rule.get("approvers", [])
                    })
            
            elif rule_type == "time_based":
                # Auto-approve during business hours
                steps.append({
                    "type": "time_based_approval",
                    "business_hours": rule.get("business_hours", {"start": "09:00", "end": "17:00"}),
                    "outside_hours_action": "manual_approval"
                })
            
            elif rule_type == "manager_approval":
                # Require manager approval
                steps.append({
                    "type": "manager_approval",
                    "manager_level": rule.get("manager_level", 1),
                    "timeout_hours": rule.get("timeout_hours", 24)
                })
            
            elif rule_type == "policy_based":
                # Check against policies
                steps.append({
                    "type": "policy_check",
                    "policies": rule.get("policies", []),
                    "violation_action": rule.get("violation_action", "reject")
                })
        
        return steps
    
    def integrate_with_access_review_workflow(
        self,
        campaign_id: str,
        review_data: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Unavailable until the deterministic response boundary is qualified."""
        block_legacy_response()

