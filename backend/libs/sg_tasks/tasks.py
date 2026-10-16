"""Celery task definitions for SentinelGrid.

Tasks are routed to dedicated queues based on their prefix:
  run_playbook_*  -> playbooks queue
  generate_report* -> reports queue
  bulk_*          -> bulk_ops queue
  agent_*         -> agents queue
"""

from __future__ import annotations

import asyncio
import logging
import os
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from sg_tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database helpers (tasks run outside FastAPI, so we create our own session)
# ---------------------------------------------------------------------------
_DB_URL = os.getenv("DB_URL", "postgresql://sg:sg@postgres:5432/sg")
_engine = create_engine(_DB_URL, pool_pre_ping=True)
_SessionFactory = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def _get_db() -> Session:
    return _SessionFactory()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Service URLs (used by PlaybookExecutor)
# ---------------------------------------------------------------------------
def _service_clients() -> Dict[str, str]:
    return {
        "iam_agent": os.getenv("IAM_AGENT_URL", "http://iam_agent:8000"),
        "siem_agent": os.getenv("SIEM_AGENT_URL", "http://siem_agent:8000"),
        "soar_agent": os.getenv("SOAR_AGENT_URL", "http://soar_agent:8000"),
    }


# ---------------------------------------------------------------------------
# Task: run_playbook_task
# ---------------------------------------------------------------------------
@celery_app.task(
    bind=True,
    name="sg_tasks.tasks.run_playbook_task",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def run_playbook_task(
    self,
    tenant_id: str,
    playbook_id: str,
    execution_id: str,
    context: dict,
) -> dict:
    """Execute a playbook asynchronously via Celery.

    Lifecycle:
      1. Load playbook definition from DB.
      2. Mark execution as ``running``.
      3. Delegate to :class:`PlaybookExecutor` for phase/step processing.
      4. Mark execution as ``completed`` or ``failed``.

    Parameters
    ----------
    tenant_id:
        Tenant UUID string.
    playbook_id:
        Playbook UUID string.
    execution_id:
        Pre-created execution UUID string.
    context:
        Runtime context (alert_id, incident_id, user params, etc.).

    Returns
    -------
    dict
        Execution result summary.
    """
    # Late import to avoid circular dependency at module load time
    from sg_tasks.playbook_executor import PlaybookExecutor

    logger.info(
        "run_playbook_task started: tenant=%s playbook=%s execution=%s",
        tenant_id,
        playbook_id,
        execution_id,
    )

    db = _get_db()
    try:
        # 1. Load playbook ------------------------------------------------
        from sg_tasks._db_helpers import load_playbook, update_execution

        playbook_row = load_playbook(db, playbook_id, tenant_id)
        if playbook_row is None:
            error_msg = f"Playbook {playbook_id} not found for tenant {tenant_id}"
            logger.error(error_msg)
            update_execution(db, execution_id, "failed", error_message=error_msg)
            return {"status": "failed", "error": error_msg}

        # 2. Mark execution running ----------------------------------------
        update_execution(db, execution_id, "running")

        # 3. Execute phases/steps ------------------------------------------
        executor = PlaybookExecutor(
            tenant_id=tenant_id,
            service_clients=_service_clients(),
        )

        # PlaybookExecutor is async; run in a dedicated event loop.
        playbook_def = {
            "id": playbook_id,
            "name": playbook_row.get("name", ""),
            "phases": playbook_row.get("phases") or [],
            "workflow": playbook_row.get("workflow") or {},
            "timeout_seconds": playbook_row.get("timeout_seconds", 3600),
        }

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                executor.execute(playbook_def, context)
            )
        finally:
            loop.close()

        # 4. Mark completed ------------------------------------------------
        update_execution(
            db,
            execution_id,
            "completed",
            results=result,
        )

        logger.info(
            "run_playbook_task completed: execution=%s steps=%d",
            execution_id,
            result.get("steps_completed", 0),
        )
        return result

    except Exception as exc:
        error_detail = traceback.format_exc()
        logger.exception(
            "run_playbook_task failed: execution=%s error=%s",
            execution_id,
            exc,
        )

        # Persist failure --------------------------------------------------
        try:
            from sg_tasks._db_helpers import update_execution

            update_execution(
                db,
                execution_id,
                "failed",
                error_message=str(exc),
                results={"traceback": error_detail},
            )
        except Exception:
            logger.exception("Failed to persist execution failure state")

        # Retry with exponential back-off ----------------------------------
        raise self.retry(exc=exc)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Task: bulk_import_task
# ---------------------------------------------------------------------------
@celery_app.task(
    bind=True,
    name="sg_tasks.tasks.bulk_import_task",
    max_retries=2,
    default_retry_delay=120,
    acks_late=True,
)
def bulk_import_task(
    self,
    tenant_id: str,
    import_type: str,
    data: List[Dict[str, Any]],
) -> dict:
    """Run a bulk import (users, entitlements, assets, etc.) asynchronously.

    Parameters
    ----------
    tenant_id:
        Tenant UUID string.
    import_type:
        Type of import (``users``, ``entitlements``, ``assets``).
    data:
        List of records to import.

    Returns
    -------
    dict
        Import summary with counts.
    """
    logger.info(
        "bulk_import_task started: tenant=%s type=%s count=%d",
        tenant_id,
        import_type,
        len(data),
    )

    db = _get_db()
    imported = 0
    skipped = 0
    errors: List[dict] = []

    try:
        for idx, record in enumerate(data):
            try:
                # Delegate to import-type-specific handler
                _handle_bulk_record(db, tenant_id, import_type, record)
                imported += 1
            except Exception as exc:
                logger.warning(
                    "bulk_import_task record %d failed: %s", idx, exc
                )
                errors.append({"index": idx, "error": str(exc)})
                skipped += 1

        db.commit()

        summary = {
            "status": "completed",
            "import_type": import_type,
            "total": len(data),
            "imported": imported,
            "skipped": skipped,
            "errors": errors[:50],  # cap error list
        }
        logger.info(
            "bulk_import_task completed: tenant=%s imported=%d skipped=%d",
            tenant_id,
            imported,
            skipped,
        )
        return summary

    except Exception as exc:
        db.rollback()
        logger.exception("bulk_import_task failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


def _handle_bulk_record(
    db: Session,
    tenant_id: str,
    import_type: str,
    record: dict,
) -> None:
    """Process a single bulk-import record.

    Override or extend this function to support additional import types.
    """
    # Placeholder: downstream services should implement specific handlers.
    logger.debug(
        "Processing %s record for tenant %s: %s",
        import_type,
        tenant_id,
        list(record.keys()),
    )


# ---------------------------------------------------------------------------
# Task: generate_report_task
# ---------------------------------------------------------------------------
@celery_app.task(
    bind=True,
    name="sg_tasks.tasks.generate_report_task",
    max_retries=2,
    default_retry_delay=90,
    acks_late=True,
)
def generate_report_task(
    self,
    tenant_id: str,
    report_id: str,
    report_type: str,
    params: dict,
) -> dict:
    """Generate a report asynchronously.

    Parameters
    ----------
    tenant_id:
        Tenant UUID string.
    report_id:
        Pre-created report UUID string.
    report_type:
        Report type (``compliance``, ``incident``, ``executive``, ``posture``).
    params:
        Report parameters (date range, filters, format, etc.).

    Returns
    -------
    dict
        Report generation result.
    """
    logger.info(
        "generate_report_task started: tenant=%s report=%s type=%s",
        tenant_id,
        report_id,
        report_type,
    )

    try:
        # Placeholder: integrate with report-generator service
        result = {
            "status": "completed",
            "report_id": report_id,
            "report_type": report_type,
            "generated_at": _utcnow().isoformat(),
            "message": "Report generation placeholder -- integrate with report-generator service",
        }
        logger.info("generate_report_task completed: report=%s", report_id)
        return result

    except Exception as exc:
        logger.exception("generate_report_task failed: %s", exc)
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Task: agent_execute_task
# ---------------------------------------------------------------------------
@celery_app.task(
    bind=True,
    name="sg_tasks.tasks.agent_execute_task",
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def agent_execute_task(
    self,
    tenant_id: str,
    task_id: str,
    agent_id: str,
) -> dict:
    """Execute an agent task (bridges Celery to agent runtime).

    Parameters
    ----------
    tenant_id:
        Tenant UUID string.
    task_id:
        Task UUID string.
    agent_id:
        Agent identifier (``siem_agent``, ``iam_agent``, ``soar_agent``).

    Returns
    -------
    dict
        Agent task execution result.
    """
    logger.info(
        "agent_execute_task started: tenant=%s task=%s agent=%s",
        tenant_id,
        task_id,
        agent_id,
    )

    try:
        # Placeholder: forward to the appropriate agent service.
        result = {
            "status": "completed",
            "task_id": task_id,
            "agent_id": agent_id,
            "completed_at": _utcnow().isoformat(),
            "message": "Agent task placeholder -- integrate with agent runtime",
        }
        logger.info(
            "agent_execute_task completed: task=%s agent=%s",
            task_id,
            agent_id,
        )
        return result

    except Exception as exc:
        logger.exception("agent_execute_task failed: %s", exc)
        raise self.retry(exc=exc)
