"""Response orchestrator - coordinates automated responses and compliance remediation."""

import logging
import httpx
from typing import Dict, Any, List, Optional
import time
from uuid import UUID
from datetime import datetime
from enum import Enum

from app.core.config import settings
from app.services.metrics import metrics_tracker

logger = logging.getLogger(__name__)


class ResponseType(str, Enum):
    """Types of responses that can be orchestrated."""
    AUTOMATED_RESPONSE = "automated_response"  # Hero Flow 4
    COMPLIANCE_REMEDIATION = "compliance_remediation"  # Hero Flow 5


class ExecutionStatus(str, Enum):
    """Execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResponseOrchestrator:
    """Orchestrates automated responses and compliance remediation workflows."""
    
    def __init__(self):
        self.automated_response_url = settings.AUTOMATED_RESPONSE_SERVICE_URL
        self.compliance_service_url = settings.COMPLIANCE_SERVICE_URL
        self.soar_agent_url = settings.SOAR_AGENT_URL
    
    def _log_op(self, *, op: str, tenant_id: UUID, status: str, duration_ms: float, **kwargs) -> None:
        """Emit a structured-ish log line for observability."""
        fields = " ".join(f"{k}={v}" for k, v in kwargs.items() if v is not None)
        logger.info(
            f"orchestration op={op} tenant={tenant_id} status={status} duration_ms={duration_ms:.2f} {fields}".strip()
        )
    
    async def orchestrate_alert_response(
        self,
        alert_id: UUID,
        tenant_id: UUID,
        response_type: ResponseType = ResponseType.AUTOMATED_RESPONSE
    ) -> Dict[str, Any]:
        """
        Orchestrate response to an alert.
        
        Args:
            alert_id: Alert ID
            tenant_id: Tenant ID
            response_type: Type of response to orchestrate
            
        Returns:
            Orchestration result
        """
        start = metrics_tracker.mark_started("automated_response")
        try:
            if response_type == ResponseType.AUTOMATED_RESPONSE:
                result = await self._orchestrate_automated_response(alert_id, tenant_id)
            else:
                raise ValueError(f"Invalid response type for alerts: {response_type}")
            duration_ms = (time.perf_counter() - start) * 1000
            metrics_tracker.mark_completed("automated_response", duration_ms)
            self._log_op(
                op="automated_response",
                tenant_id=tenant_id,
                status="completed",
                duration_ms=duration_ms,
                alert_id=alert_id,
                playbooks_triggered=result.get("playbooks_triggered"),
            )
            return result
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            metrics_tracker.mark_failed("automated_response", duration_ms)
            self._log_op(
                op="automated_response",
                tenant_id=tenant_id,
                status="failed",
                duration_ms=duration_ms,
                alert_id=alert_id,
            )
            raise
    
    async def orchestrate_finding_remediation(
        self,
        finding_id: UUID,
        finding_type: str,
        tenant_id: UUID,
        playbook_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Orchestrate remediation for a compliance finding.
        
        Args:
            finding_id: Finding ID
            finding_type: 'iam_finding' or 'posture_finding'
            tenant_id: Tenant ID
            playbook_id: Optional specific playbook ID
            
        Returns:
            Orchestration result
        """
        start = metrics_tracker.mark_started("compliance_remediation")
        try:
            result = await self._orchestrate_compliance_remediation(
                finding_id, finding_type, tenant_id, playbook_id
            )
            duration_ms = (time.perf_counter() - start) * 1000
            metrics_tracker.mark_completed("compliance_remediation", duration_ms)
            self._log_op(
                op="compliance_remediation",
                tenant_id=tenant_id,
                status="completed",
                duration_ms=duration_ms,
                finding_id=finding_id,
                finding_type=finding_type,
                playbook_id=playbook_id,
            )
            return result
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            metrics_tracker.mark_failed("compliance_remediation", duration_ms)
            self._log_op(
                op="compliance_remediation",
                tenant_id=tenant_id,
                status="failed",
                duration_ms=duration_ms,
                finding_id=finding_id,
                finding_type=finding_type,
                playbook_id=playbook_id,
            )
            raise
    
    async def _orchestrate_automated_response(
        self,
        alert_id: UUID,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """
        Orchestrate automated response for an alert.
        
        Flow:
        1. Evaluate alert against playbook triggers
        2. Trigger matching playbooks
        3. Track execution status
        4. Handle failures and retries
        """
        try:
            # Step 1: Evaluate alert triggers
            evaluation_result = await self._evaluate_alert_triggers(alert_id, tenant_id)
            
            if not evaluation_result.get("matching_playbooks"):
                return {
                    "alert_id": str(alert_id),
                    "status": "no_triggers",
                    "message": "No matching playbooks found for alert"
                }
            
            # Step 2: Trigger playbooks
            triggered_playbooks = []
            for playbook in evaluation_result["matching_playbooks"]:
                try:
                    trigger_result = await self._trigger_playbook(
                        alert_id=alert_id,
                        playbook_id=playbook["playbook_id"],
                        tenant_id=tenant_id,
                        trigger_reason=playbook["trigger_reason"]
                    )
                    triggered_playbooks.append({
                        "playbook_id": str(playbook["playbook_id"]),
                        "playbook_name": playbook["playbook_name"],
                        "execution_id": trigger_result.get("execution_id"),
                        "status": trigger_result.get("status", "pending")
                    })
                except Exception as e:
                    logger.error(
                        f"Failed to trigger playbook {playbook['playbook_id']} for alert {alert_id}: {e}",
                        exc_info=True
                    )
                    triggered_playbooks.append({
                        "playbook_id": str(playbook["playbook_id"]),
                        "playbook_name": playbook["playbook_name"],
                        "status": "failed",
                        "error": str(e)
                    })
            
            return {
                "alert_id": str(alert_id),
                "status": "orchestrated",
                "playbooks_triggered": len(triggered_playbooks),
                "playbooks": triggered_playbooks,
                "orchestrated_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error orchestrating automated response for alert {alert_id}: {e}", exc_info=True)
            raise
    
    async def _orchestrate_compliance_remediation(
        self,
        finding_id: UUID,
        finding_type: str,
        tenant_id: UUID,
        playbook_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Orchestrate compliance remediation for a finding.
        
        Flow:
        1. Enhance finding with compliance metadata (if not already done)
        2. Create remediation plan (if not exists)
        3. Execute remediation via playbook
        4. Track execution status
        """
        try:
            # Step 1: Enhance finding (if needed)
            enhancement_result = await self._enhance_finding(finding_id, finding_type, tenant_id)
            
            # Step 2: Create remediation plan (if needed)
            if not enhancement_result.get("remediation_plan"):
                plan_result = await self._create_remediation_plan(
                    finding_id, finding_type, tenant_id
                )
                remediation_plan = plan_result.get("plan", {})
            else:
                remediation_plan = enhancement_result["remediation_plan"]
            
            # Step 3: Execute remediation
            execution_result = await self._execute_remediation(
                finding_id=finding_id,
                finding_type=finding_type,
                tenant_id=tenant_id,
                playbook_id=playbook_id
            )
            
            return {
                "finding_id": str(finding_id),
                "finding_type": finding_type,
                "status": "orchestrated",
                "remediation_id": execution_result.get("remediation_id"),
                "execution_id": execution_result.get("execution_id"),
                "remediation_plan": remediation_plan,
                "orchestrated_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(
                f"Error orchestrating compliance remediation for {finding_type} {finding_id}: {e}",
                exc_info=True
            )
            raise
    
    async def _evaluate_alert_triggers(
        self,
        alert_id: UUID,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Evaluate alert against playbook triggers."""
        url = f"{self.automated_response_url}/api/v1/automated-response/alerts/{alert_id}/evaluate"
        
        headers = {
            "X-Tenant-ID": str(tenant_id),
            "Content-Type": "application/json"
        }
        
        if settings.INTERNAL_SERVICE_TOKEN:
            headers["Authorization"] = f"Bearer {settings.INTERNAL_SERVICE_TOKEN}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def _trigger_playbook(
        self,
        alert_id: UUID,
        playbook_id: UUID,
        tenant_id: UUID,
        trigger_reason: str
    ) -> Dict[str, Any]:
        """Trigger a playbook for an alert."""
        url = f"{self.automated_response_url}/api/v1/automated-response/alerts/{alert_id}/trigger"
        
        payload = {
            "playbook_id": str(playbook_id),
            "trigger_reason": trigger_reason
        }
        
        headers = {
            "X-Tenant-ID": str(tenant_id),
            "Content-Type": "application/json"
        }
        
        if settings.INTERNAL_SERVICE_TOKEN:
            headers["Authorization"] = f"Bearer {settings.INTERNAL_SERVICE_TOKEN}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def _enhance_finding(
        self,
        finding_id: UUID,
        finding_type: str,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Enhance finding with compliance metadata."""
        url = f"{self.compliance_service_url}/api/v1/compliance/findings/{finding_id}/enhance"
        
        payload = {
            "finding_type": finding_type
        }
        
        headers = {
            "X-Tenant-ID": str(tenant_id),
            "Content-Type": "application/json"
        }
        
        if settings.INTERNAL_SERVICE_TOKEN:
            headers["Authorization"] = f"Bearer {settings.INTERNAL_SERVICE_TOKEN}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Finding might not exist yet, return empty result
                    return {}
                raise
    
    async def _create_remediation_plan(
        self,
        finding_id: UUID,
        finding_type: str,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Create remediation plan for a finding."""
        url = f"{self.compliance_service_url}/api/v1/compliance/findings/{finding_id}/remediation-plan"
        
        payload = {
            "finding_type": finding_type
        }
        
        headers = {
            "X-Tenant-ID": str(tenant_id),
            "Content-Type": "application/json"
        }
        
        if settings.INTERNAL_SERVICE_TOKEN:
            headers["Authorization"] = f"Bearer {settings.INTERNAL_SERVICE_TOKEN}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def _execute_remediation(
        self,
        finding_id: UUID,
        finding_type: str,
        tenant_id: UUID,
        playbook_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Execute remediation for a finding."""
        url = f"{self.compliance_service_url}/api/v1/compliance/findings/{finding_id}/remediate"
        
        payload = {
            "playbook_id": str(playbook_id) if playbook_id else None,
            "auto_approve": False
        }
        
        headers = {
            "X-Tenant-ID": str(tenant_id),
            "Content-Type": "application/json"
        }
        
        if settings.INTERNAL_SERVICE_TOKEN:
            headers["Authorization"] = f"Bearer {settings.INTERNAL_SERVICE_TOKEN}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
                params={"finding_type": finding_type}
            )
            response.raise_for_status()
            return response.json()
    
    async def get_execution_status(
        self,
        execution_id: UUID,
        tenant_id: UUID,
        execution_type: str = "playbook"
    ) -> Dict[str, Any]:
        """
        Get execution status.
        
        Args:
            execution_id: Execution ID
            tenant_id: Tenant ID
            execution_type: 'playbook' or 'remediation'
            
        Returns:
            Execution status
        """
        if execution_type == "playbook":
            url = f"{self.soar_agent_url}/soar/executions/{execution_id}"
        else:
            # For remediation, query compliance service
            # This would need a new endpoint or we query the database directly
            raise NotImplementedError("Remediation status query not yet implemented")
        
        headers = {
            "X-Tenant-ID": str(tenant_id)
        }
        
        if settings.INTERNAL_SERVICE_TOKEN:
            headers["Authorization"] = f"Bearer {settings.INTERNAL_SERVICE_TOKEN}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    
    async def generate_execution_report(
        self,
        tenant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate execution report for orchestrated responses.
        
        Args:
            tenant_id: Tenant ID
            start_date: Start date for report
            end_date: End date for report
            
        Returns:
            Execution report
        """
        # This would aggregate data from multiple services
        # For now, return a stub
        return {
            "tenant_id": str(tenant_id),
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "summary": {
                "total_orchestrations": 0,
                "successful": 0,
                "failed": 0,
                "in_progress": 0
            },
            "by_type": {
                "automated_response": 0,
                "compliance_remediation": 0
            }
        }
