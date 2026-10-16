"""Finding enhancer - adds compliance metadata to existing findings."""

import logging
import httpx
from typing import Dict, Any, Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, update, Table, MetaData

# Import from sg_core for shared models
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))
from sg_core.models import IAMFinding, PostureFinding
from sg_core.service_security import build_internal_auth_headers
from app.core.config import settings

logger = logging.getLogger(__name__)


class FindingEnhancer:
    """Enhances existing findings with compliance metadata."""
    
    def __init__(self, db: Session):
        self.db = db
        self.framework_service_url = settings.FRAMEWORK_SERVICE_URL
        # Cache mappings per process to reduce framework service calls
        self._soc2_cache: Dict[str, List[Dict[str, Any]]] = {}
    
    async def enhance_iam_finding(
        self,
        finding_id: UUID,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """
        Enhance an existing IAM finding with compliance metadata.
        
        Args:
            finding_id: IAM finding ID
            tenant_id: Tenant ID
            
        Returns:
            Enhanced finding data
        """
        finding = self.db.query(IAMFinding).filter(
            and_(IAMFinding.id == finding_id, IAMFinding.tenant_id == tenant_id)
        ).first()
        
        if not finding:
            raise ValueError(f"IAM finding {finding_id} not found for tenant {tenant_id}")
        
        # Map finding type to NIST control
        nist_control_id = await self._map_to_nist_control(finding.finding_type, "iam", tenant_id)
        soc2_criteria = await self._map_to_soc2_criteria(finding.finding_type, "iam", tenant_id)
        
        # Generate remediation plan
        remediation_plan = self._generate_remediation_plan(finding)
        
        # Update finding with compliance metadata (only set SOC2 if model supports it)
        finding.nist_control_id = nist_control_id
        if hasattr(finding, "soc2_criteria"):
            finding.soc2_criteria = soc2_criteria or []
        finding.remediation_plan = remediation_plan
        
        self.db.commit()
        self.db.refresh(finding)
        
        logger.info(f"Enhanced IAM finding {finding_id} with compliance metadata")
        
        return {
            "finding_id": str(finding.id),
            "nist_control_id": nist_control_id,
            "soc2_criteria": soc2_criteria or [],
            "remediation_plan": remediation_plan,
            "remediation_status": finding.remediation_status
        }
    
    async def enhance_posture_finding(
        self,
        finding_id: UUID,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """
        Enhance an existing Posture finding with compliance metadata.
        
        Args:
            finding_id: Posture finding ID
            tenant_id: Tenant ID
            
        Returns:
            Enhanced finding data
        """
        finding = self.db.query(PostureFinding).filter(
            and_(PostureFinding.id == finding_id, PostureFinding.tenant_id == tenant_id)
        ).first()
        
        if not finding:
            raise ValueError(f"Posture finding {finding_id} not found for tenant {tenant_id}")
        
        # Map finding to NIST control
        nist_control_id = await self._map_to_nist_control(finding.check_id or finding.title, "posture", tenant_id)
        soc2_criteria = await self._map_to_soc2_criteria(finding.check_id or finding.title, "posture", tenant_id)
        
        # Generate remediation plan
        remediation_plan = self._generate_remediation_plan(finding)
        
        # Update finding with compliance metadata (only set SOC2 if model supports it)
        finding.nist_control_id = nist_control_id
        if hasattr(finding, "soc2_criteria"):
            finding.soc2_criteria = soc2_criteria or []
        finding.remediation_plan = remediation_plan
        
        self.db.commit()
        self.db.refresh(finding)
        
        logger.info(f"Enhanced Posture finding {finding_id} with compliance metadata")
        
        return {
            "finding_id": str(finding.id),
            "nist_control_id": nist_control_id,
            "soc2_criteria": soc2_criteria or [],
            "remediation_plan": remediation_plan,
            "remediation_status": finding.remediation_status
        }
    
    async def _map_to_nist_control(
        self,
        finding_identifier: str,
        finding_type: str,
        tenant_id: UUID,
    ) -> Optional[str]:
        """
        Map finding to NIST SP 800-53 control.
        
        Args:
            finding_identifier: Finding type (for IAM) or check_id (for Posture)
            finding_type: 'iam' or 'posture'
            
        Returns:
            NIST control ID or None
        """
        try:
            # Call Framework Service to map finding to NIST control
            url = f"{self.framework_service_url}/api/v1/framework/map-to-nist"
            
            payload = {
                "finding_type": finding_type,
                "finding_identifier": finding_identifier,
                "tenant_id": str(tenant_id),
            }
            
            headers = build_internal_auth_headers(
                settings.INTERNAL_SERVICE_TOKEN or "",
                tenant_id=tenant_id,
                extra_headers={"Content-Type": "application/json"},
            )
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    result = response.json()
                    return result.get("nist_control_id")
                else:
                    logger.warning(f"Framework service returned {response.status_code} for NIST mapping")
                    return None
        
        except Exception as e:
            logger.error(f"Error mapping to NIST control: {e}", exc_info=True)
            return None

    async def _map_to_soc2_criteria(
        self,
        finding_identifier: str,
        finding_type: str,
        tenant_id: UUID,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Map finding to SOC 2 Common Criteria via Framework Service.
        """
        cache_key = f"{tenant_id}:{finding_type}:{finding_identifier}"
        if cache_key in self._soc2_cache:
            return self._soc2_cache[cache_key]

        try:
            url = f"{self.framework_service_url}/api/v1/framework/map-to-soc2"
            payload = {
                "finding_type": finding_type,
                "finding_identifier": finding_identifier,
                "severity": "medium",
                "tenant_id": str(tenant_id),
            }
            headers = build_internal_auth_headers(
                settings.INTERNAL_SERVICE_TOKEN or "",
                tenant_id=tenant_id,
                extra_headers={"Content-Type": "application/json"},
            )

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    soc2 = data.get("soc2_criteria", [])
                    self._soc2_cache[cache_key] = soc2
                    return soc2
                logger.warning(f"Framework service returned {response.status_code} for SOC 2 mapping")
                return None
        except Exception as e:
            logger.error(f"Error mapping to SOC 2 criteria: {e}", exc_info=True)
            return None
    
    def _generate_remediation_plan(self, finding: Any) -> Dict[str, Any]:
        """
        Generate remediation plan for a finding.
        
        Args:
            finding: IAMFinding or PostureFinding object
            
        Returns:
            Structured remediation plan
        """
        plan = {
            "steps": [],
            "estimated_time": "unknown",
            "complexity": "medium",
            "requires_approval": True
        }
        
        # Generate steps based on finding type
        if isinstance(finding, IAMFinding):
            plan["steps"] = self._generate_iam_remediation_steps(finding)
        elif isinstance(finding, PostureFinding):
            plan["steps"] = self._generate_posture_remediation_steps(finding)
        
        # Use existing recommendation if available
        if hasattr(finding, 'recommendation') and finding.recommendation:
            plan["description"] = finding.recommendation
        elif hasattr(finding, 'remediation') and finding.remediation:
            plan["description"] = finding.remediation
        
        return plan
    
    def _generate_iam_remediation_steps(self, finding: IAMFinding) -> list:
        """Generate remediation steps for IAM finding."""
        steps = []
        
        if finding.finding_type == "dormant_account":
            steps = [
                {
                    "step": 1,
                    "action": "Review account activity",
                    "description": "Verify account has been inactive for required period"
                },
                {
                    "step": 2,
                    "action": "Disable account",
                    "description": "Disable the dormant account via IAM Agent",
                    "playbook_action": "disable_user"
                },
                {
                    "step": 3,
                    "action": "Notify user",
                    "description": "Send notification to user about account status",
                    "playbook_action": "notify_user"
                }
            ]
        elif finding.finding_type == "overprivileged":
            steps = [
                {
                    "step": 1,
                    "action": "Review permissions",
                    "description": "Analyze current permissions and identify excessive access"
                },
                {
                    "step": 2,
                    "action": "Remove excessive permissions",
                    "description": "Remove unnecessary roles/permissions",
                    "playbook_action": "remove_permissions"
                },
                {
                    "step": 3,
                    "action": "Verify access",
                    "description": "Verify user still has required access for their role"
                }
            ]
        else:
            steps = [
                {
                    "step": 1,
                    "action": "Review finding",
                    "description": finding.description or "Review the finding details"
                },
                {
                    "step": 2,
                    "action": "Apply remediation",
                    "description": finding.recommendation or "Apply recommended remediation"
                }
            ]
        
        return steps
    
    def _generate_posture_remediation_steps(self, finding: PostureFinding) -> list:
        """Generate remediation steps for Posture finding."""
        steps = []
        
        # Use existing remediation if available
        if finding.remediation:
            steps = [
                {
                    "step": 1,
                    "action": "Review misconfiguration",
                    "description": finding.description
                },
                {
                    "step": 2,
                    "action": "Apply fix",
                    "description": finding.remediation,
                    "playbook_action": "remediate_posture"
                }
            ]
        else:
            steps = [
                {
                    "step": 1,
                    "action": "Review finding",
                    "description": finding.description
                },
                {
                    "step": 2,
                    "action": "Apply remediation",
                    "description": "Follow framework-specific remediation guidance"
                }
            ]
        
        return steps
