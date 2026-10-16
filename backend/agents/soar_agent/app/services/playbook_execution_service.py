"""Playbook execution service for coordinating workflow execution.

Playbook execution is delegated to Celery workers via ``run_playbook_task``
so that the API returns immediately and the playbook runs asynchronously.
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta

from sg_agent_runtime.soc_case_runtime_client import SOCCaseRuntimeClient

from app.database import PlaybookExecutionORM
from app.core.config import settings
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy Celery task import -- avoids hard dependency if Celery is not installed
# in the SOAR agent image (the task is submitted to a separate worker).
# ---------------------------------------------------------------------------
_celery_available = True
try:
    from sg_tasks.tasks import run_playbook_task as _run_playbook_task
except ImportError:
    _celery_available = False
    _run_playbook_task = None  # type: ignore[assignment]
    logger.warning(
        "sg_tasks not available; playbook execution will remain pending until a worker is connected"
    )


class PlaybookExecutionService:
    """Service for executing playbooks and managing execution state."""

    def __init__(self, db: Session):
        self.db = db

    def _extract_incident_id(self, execution: PlaybookExecutionORM) -> str | None:
        logs = execution.logs or {}
        if isinstance(logs, dict):
            incident_id = logs.get("incident_id")
            if incident_id:
                return str(incident_id)
            if logs.get("trigger_type") == "incident" and logs.get("trigger_id"):
                return str(logs["trigger_id"])
            parameters = logs.get("parameters") or {}
            if isinstance(parameters, dict) and parameters.get("incident_id"):
                return str(parameters["incident_id"])
        return None

    def _submit_soc_case_refresh_for_execution(
        self,
        execution: PlaybookExecutionORM,
        *,
        status: str,
    ) -> dict | None:
        incident_id = self._extract_incident_id(execution)
        if not incident_id or status not in {"completed", "failed", "cancelled"}:
            return None

        client = SOCCaseRuntimeClient(
            runtime_url=getattr(settings, "AGENT_RUNTIME_URL", None),
            internal_token=settings.INTERNAL_SERVICE_TOKEN,
        )
        return client.submit_case_refresh_sync(
            tenant_id=str(execution.tenant_id),
            incident_id=incident_id,
            trigger_type="playbook_execution_completed",
            source_kind="playbook_execution",
            source_event_id=str(execution.id),
            changed_fields=["playbook_execution_status", "playbook_execution_results"],
            reason=f"Playbook execution moved to terminal status '{status}'.",
            payload={
                "playbook_execution_id": str(execution.id),
                "playbook_execution_status": status,
                "workflow_exec_id": execution.workflow_exec_id,
            },
        )

    def create_execution(
        self,
        tenant_id: str,
        playbook_id: UUID,
        triggered_by: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> PlaybookExecutionORM:
        """
        Create a new playbook execution record.
        
        Args:
            tenant_id: Tenant ID
            playbook_id: Playbook ID
            triggered_by: User ID or system identifier
            context: Optional context data (alert_id, incident_id, etc.)
        
        Returns:
            Playbook execution record
        """
        execution = PlaybookExecutionORM(
            tenant_id=tenant_id,
            playbook_id=playbook_id,
            status="pending",
            triggered_by=triggered_by,
            started_at=datetime.utcnow(),
        )
        # Store context in logs for downstream traceability
        if context:
            execution.logs = context
            
        self.db.add(execution)
        self.db.commit()
        self.db.refresh(execution)
        
        logger.info(f"Created playbook execution {execution.id} for playbook {playbook_id}")
        return execution

    def update_execution_status(
        self,
        execution_id: UUID,
        status: str,
        workflow_exec_id: Optional[str] = None,
        logs: Optional[Dict[str, Any]] = None,
        results: Optional[Dict[str, Any]] = None,
    ) -> PlaybookExecutionORM:
        """
        Update execution status and results.
        
        Args:
            execution_id: Execution ID
            status: New status (pending, running, completed, failed, cancelled)
            workflow_exec_id: Optional workflow execution ID from n8n
            logs: Optional execution logs
            results: Optional execution results
        
        Returns:
            Updated execution record
        """
        execution = self.db.query(PlaybookExecutionORM).filter(
            PlaybookExecutionORM.id == execution_id
        ).first()
        
        if not execution:
            raise ValueError(f"Execution {execution_id} not found")
        
        execution.status = status
        execution.last_updated_at = datetime.utcnow()
        
        if workflow_exec_id:
            execution.workflow_exec_id = workflow_exec_id
        
        if logs:
            if execution.logs:
                execution.logs.update(logs)
            else:
                execution.logs = logs
        
        if results:
            execution.results = results
        
        if status in ["completed", "failed", "cancelled"]:
            execution.finished_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(execution)

        try:
            self._submit_soc_case_refresh_for_execution(execution, status=status)
        except Exception as exc:
            logger.warning(
                "Failed submitting SOC case refresh for playbook execution %s: %s",
                execution.id,
                exc,
            )

        logger.info(f"Updated execution {execution_id} status to {status}")
        return execution

    def get_execution(self, execution_id: UUID, tenant_id: str) -> Optional[PlaybookExecutionORM]:
        """
        Get execution by ID with tenant isolation.
        
        Args:
            execution_id: Execution ID
            tenant_id: Tenant ID for isolation
        
        Returns:
            Execution record or None
        """
        return self.db.query(PlaybookExecutionORM).filter(
            PlaybookExecutionORM.id == execution_id,
            PlaybookExecutionORM.tenant_id == tenant_id
        ).first()

    def list_executions(
        self,
        tenant_id: str,
        playbook_id: Optional[UUID] = None,
        status: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[PlaybookExecutionORM]:
        """
        List executions with optional filters.
        
        Args:
            tenant_id: Tenant ID
            playbook_id: Optional playbook filter
            status: Optional status filter
            limit: Maximum results
            skip: Results to skip
        
        Returns:
            List of execution records
        """
        query = self.db.query(PlaybookExecutionORM).filter(
            PlaybookExecutionORM.tenant_id == tenant_id
        )
        
        if playbook_id:
            query = query.filter(PlaybookExecutionORM.playbook_id == playbook_id)
        
        if status:
            query = query.filter(PlaybookExecutionORM.status == status)
        
        return query.order_by(PlaybookExecutionORM.started_at.desc()).offset(skip).limit(limit).all()

    async def execute_playbook(
        self,
        tenant_id: str,
        playbook_id: UUID,
        triggered_by: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> PlaybookExecutionORM:
        """Execute a playbook asynchronously via Celery.

        1. Creates the execution record in the database.
        2. Submits a ``run_playbook_task`` to the Celery playbooks queue.
        3. Returns the execution record immediately (the worker picks it up).

        If Celery / ``sg_tasks`` is unavailable the method leaves the
        execution in ``pending`` with an explanatory result payload so the
        API remains truthful during local development.

        Args:
            tenant_id: Tenant ID
            playbook_id: Playbook ID
            triggered_by: User ID or system identifier
            context: Optional context data

        Returns:
            Execution record (status will be ``pending`` until the worker
            picks it up).
        """
        # 1. Create execution record in DB ---------------------------------
        execution = self.create_execution(
            tenant_id=tenant_id,
            playbook_id=playbook_id,
            triggered_by=triggered_by,
            context=context,
        )

        logger.info(
            "Submitting playbook execution: playbook=%s execution=%s tenant=%s",
            playbook_id,
            execution.id,
            tenant_id,
        )

        # 2. Submit Celery task --------------------------------------------
        if _celery_available and _run_playbook_task is not None:
            try:
                celery_result = _run_playbook_task.delay(
                    tenant_id=str(tenant_id),
                    playbook_id=str(playbook_id),
                    execution_id=str(execution.id),
                    context=context or {},
                )

                # Store the Celery task ID in the workflow_exec_id column
                # (repurposed from the former n8n execution ID).
                execution = self.update_execution_status(
                    execution.id,
                    "pending",
                    workflow_exec_id=celery_result.id,
                )

                logger.info(
                    "Celery task submitted: celery_task_id=%s execution=%s",
                    celery_result.id,
                    execution.id,
                )
            except Exception as exc:
                logger.exception(
                    "Failed to submit Celery task for execution %s: %s",
                    execution.id,
                    exc,
                )
                execution = self.update_execution_status(
                    execution.id,
                    "failed",
                    results={"error": f"Failed to submit async task: {exc}"},
                )
        else:
            # Fallback: keep the request pending until a worker is available.
            logger.warning(
                "Celery not available; execution %s will remain pending",
                execution.id,
            )
            execution = self.update_execution_status(
                execution.id,
                "pending",
                results={
                    "message": "Execution request recorded, but no SOAR worker is currently connected.",
                },
                logs={
                    "worker_state": "unavailable",
                },
            )

        return execution
