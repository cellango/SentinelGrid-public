"""
Workflow Integration Service
Integrates IAM Agent with SOAR playbooks and workflow engines
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx

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
        """
        Trigger a SOAR playbook for IAM-related incidents.
        
        Common playbooks:
        - user_compromise_response
        - privilege_escalation_response
        - access_violation_response
        - compliance_remediation
        """
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.soar_url}/internal/soar/playbooks/{playbook_id}/execute",
                    json={
                        "incident": incident_data,
                        "tenant_id": tenant_id,
                        "triggered_by": "iam_agent",
                        "triggered_at": datetime.utcnow().isoformat()
                    }
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Error triggering SOAR playbook: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error triggering SOAR playbook: {e}")
            raise
    
    def create_automated_approval_workflow(
        self,
        request_type: str,
        request_data: Dict[str, Any],
        approval_rules: List[Dict[str, Any]],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an automated approval workflow for access requests.
        
        Approval rules can include:
        - Risk-based approval (auto-approve low risk, require approval for high risk)
        - Time-based approval (auto-approve during business hours)
        - Manager approval requirements
        - Policy-based approval
        """
        workflow_definition = {
            "name": f"automated_approval_{request_type}",
            "type": "approval_workflow",
            "tenant_id": tenant_id,
            "trigger": {
                "type": "access_request",
                "request_type": request_type
            },
            "steps": self._build_approval_steps(approval_rules, request_data),
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.workflow_engine_url}/internal/workflows",
                    json=workflow_definition
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error creating approval workflow: {e}")
            raise
    
    def execute_remediation_workflow(
        self,
        violation_type: str,
        violation_data: Dict[str, Any],
        remediation_steps: List[str],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute an automated remediation workflow.
        """
        workflow_execution = {
            "workflow_type": "iam_remediation",
            "violation_type": violation_type,
            "violation_data": violation_data,
            "remediation_steps": remediation_steps,
            "tenant_id": tenant_id,
            "executed_at": datetime.utcnow().isoformat()
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.workflow_engine_url}/internal/workflows/execute",
                    json=workflow_execution
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error executing remediation workflow: {e}")
            raise
    
    def get_workflow_status(
        self,
        workflow_execution_id: str
    ) -> Dict[str, Any]:
        """Get status of a workflow execution."""
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.workflow_engine_url}/internal/workflows/{workflow_execution_id}/status"
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error getting workflow status: {e}")
            raise
    
    def create_risk_response_playbook(
        self,
        risk_level: str,
        user_id: str,
        risk_details: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create and execute a risk response playbook.
        """
        playbook_name = f"risk_response_{risk_level}"
        
        playbook_data = {
            "playbook": playbook_name,
            "incident": {
                "type": "iam_risk",
                "severity": risk_level,
                "user_id": user_id,
                "details": risk_details,
                "tenant_id": tenant_id
            },
            "auto_execute": risk_level in ["critical", "high"]
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.soar_url}/internal/soar/playbooks/{playbook_name}/execute",
                    json=playbook_data
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error creating risk response playbook: {e}")
            raise
    
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
        """
        Integrate with access review campaign workflows.
        """
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.workflow_engine_url}/internal/workflows/access_review",
                    json={
                        "campaign_id": campaign_id,
                        "review_data": review_data,
                        "tenant_id": tenant_id
                    }
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            logger.error(f"Error integrating with access review workflow: {e}")
            raise

