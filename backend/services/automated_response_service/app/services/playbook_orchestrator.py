"""Playbook orchestrator - triggers playbooks via SOAR Agent."""

import logging
import httpx
import json
from typing import Dict, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, update

# Import from sg_core for shared models
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../libs"))
from sg_core.models import Alert, AlertPlaybookTrigger, PlaybookExecution
from app.core.config import settings

logger = logging.getLogger(__name__)


class PlaybookOrchestrator:
    """Orchestrator for triggering playbooks via SOAR Agent."""
    
    def __init__(self, db: Session):
        self.db = db
        self.soar_agent_url = settings.SOAR_AGENT_URL
    
    async def trigger_playbook(
        self,
        playbook_id: UUID,
        alert_id: UUID,
        tenant_id: UUID,
        trigger_reason: str
    ) -> Dict[str, Any]:
        """
        Trigger a playbook for an alert via SOAR Agent.
        
        Args:
            playbook_id: Playbook ID to trigger
            alert_id: Alert ID that triggered the playbook
            tenant_id: Tenant ID
            trigger_reason: Reason why playbook was triggered
            
        Returns:
            Execution result with execution_id and status
        """
        # Get alert
        alert = self.db.query(Alert).filter(
            and_(Alert.id == alert_id, Alert.tenant_id == tenant_id)
        ).first()
        
        if not alert:
            raise ValueError(f"Alert {alert_id} not found for tenant {tenant_id}")
        
        # Create trigger metadata record
        trigger_record = AlertPlaybookTrigger(
            id=uuid4(),
            tenant_id=tenant_id,
            alert_id=alert_id,
            playbook_id=playbook_id,
            trigger_reason=trigger_reason,
            evaluated_at=datetime.utcnow()
        )
        self.db.add(trigger_record)
        
        try:
            # Call SOAR Agent to execute playbook
            execution_result = await self._execute_playbook_via_soar(
                playbook_id=playbook_id,
                alert_id=alert_id,
                tenant_id=tenant_id
            )

            # Persist execution in core table for traceability
            execution = self._record_execution(
                playbook_id=playbook_id,
                alert=alert,
                tenant_id=tenant_id,
                execution_result=execution_result,
                triggered_by="automated_response",
            )
            
            # Update trigger record with execution ID
            if execution and execution.id:
                trigger_record.playbook_execution_id = execution.id
                trigger_record.triggered_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(
                f"Triggered playbook {playbook_id} for alert {alert_id}. "
                f"Execution ID: {getattr(execution, 'id', None) or execution_result.get('execution_id')}"
            )
            
            return {
                "trigger_id": str(trigger_record.id),
                "execution_id": str(execution.id) if execution else execution_result.get("execution_id"),
                "status": (execution.status if execution else execution_result.get("status")) or "pending",
                "trigger_reason": trigger_reason
            }
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to trigger playbook {playbook_id} for alert {alert_id}: {e}", exc_info=True)
            raise
    
    async def _execute_playbook_via_soar(
        self,
        playbook_id: UUID,
        alert_id: UUID,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """
        Execute playbook via SOAR Agent.
        
        Args:
            playbook_id: Playbook ID
            alert_id: Alert ID
            tenant_id: Tenant ID
            
        Returns:
            Execution result from SOAR Agent
        """
        url = f"{self.soar_agent_url}/internal/soar/playbooks/{playbook_id}/execute"
        
        payload = {
            "tenant_id": str(tenant_id),
            "target_type": "alert",
            "target_id": str(alert_id),
            "triggered_by": "automated_response",
            "params": {
                "alert_id": str(alert_id),
                "trigger_source": "automated_response_service"
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

    def _extract_detection_from_alert(self, alert: Alert) -> tuple[Optional[str], Optional[str]]:
        """Pull detection rule identifiers from the alert payload."""
        payload = alert.raw_payload or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}

        sg_ctx = payload.get("sg") or {}
        rule_ctx = payload.get("rule") or {}

        det_id = (
            payload.get("detection_rule_id")
            or sg_ctx.get("detection_rule_id")
            or sg_ctx.get("rule_id")
            or rule_ctx.get("id")
            or rule_ctx.get("rule_id")
            or payload.get("rule_id")
        )
        det_ver = (
            payload.get("detection_rule_version_id")
            or sg_ctx.get("detection_rule_version_id")
            or sg_ctx.get("rule_version")
            or rule_ctx.get("version_id")
            or rule_ctx.get("version")
            or payload.get("rule_version")
        )

        return (str(det_id) if det_id else None, str(det_ver) if det_ver else None)

    def _record_execution(
        self,
        playbook_id: UUID,
        alert: Alert,
        tenant_id: UUID,
        execution_result: Dict[str, Any],
        triggered_by: str,
    ) -> Optional[PlaybookExecution]:
        """
        Persist a playbook execution record into the shared DB so UI traceability works.
        """
        try:
            status = execution_result.get("status") or "pending"
            workflow_exec_id = execution_result.get("workflow_exec_id")
            exec_id_raw = execution_result.get("execution_id")
            exec_uuid = None
            if exec_id_raw:
                try:
                    exec_uuid = UUID(str(exec_id_raw))
                except Exception:
                    exec_uuid = None

            det_id, det_ver = self._extract_detection_from_alert(alert)

            execution = PlaybookExecution(
                id=exec_uuid,
                tenant_id=tenant_id,
                playbook_id=playbook_id,
                target_type="alert",
                target_id=alert.id,
                status=status,
                workflow_exec_id=workflow_exec_id,
                triggered_by=triggered_by,
                approval_status="approved",
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow() if status in ("completed", "failed", "cancelled") else None,
                result_summary=execution_result.get("message"),
                logs={
                    "detection_rule_id": det_id,
                    "detection_rule_version_id": det_ver,
                    "execution_result": execution_result,
                },
                alert_id=alert.id,
                trigger_rule_id=None,
            )
            self.db.add(execution)
            self.db.flush()
            return execution
        except Exception as e:
            logger.error(f"Failed to record playbook execution traceability: {e}", exc_info=True)
            return None
    
    def update_execution_link(
        self,
        trigger_id: UUID,
        execution_id: UUID,
        tenant_id: UUID
    ) -> None:
        """
        Update trigger record with execution ID after playbook execution is created.
        
        Args:
            trigger_id: Trigger record ID
            execution_id: Playbook execution ID
            tenant_id: Tenant ID
        """
        trigger = self.db.query(AlertPlaybookTrigger).filter(
            and_(
                AlertPlaybookTrigger.id == trigger_id,
                AlertPlaybookTrigger.tenant_id == tenant_id
            )
        ).first()
        
        if trigger:
            trigger.playbook_execution_id = execution_id
            trigger.triggered_at = datetime.utcnow()
            self.db.commit()
            logger.info(f"Updated trigger {trigger_id} with execution {execution_id}")
