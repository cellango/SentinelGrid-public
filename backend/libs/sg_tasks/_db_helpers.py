"""Database helper functions for Celery tasks.

These run outside FastAPI, so they operate on raw SQLAlchemy sessions
and use text queries to stay decoupled from any single agent's ORM models.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def load_playbook(
    db: Session,
    playbook_id: str,
    tenant_id: str,
) -> Optional[Dict[str, Any]]:
    """Load a playbook definition from the database.

    Returns a plain dict with the columns needed for execution,
    or ``None`` if not found.
    """
    result = db.execute(
        text(
            """
            SELECT id, tenant_id, name, description, category,
                   phases, workflow, timeout_seconds, retry_policy,
                   on_failure, requires_approval, is_enabled
            FROM playbooks
            WHERE id = :pid AND tenant_id = :tid
            """
        ),
        {"pid": playbook_id, "tid": tenant_id},
    ).fetchone()

    if result is None:
        return None

    return dict(result._mapping)


def update_execution(
    db: Session,
    execution_id: str,
    status: str,
    *,
    error_message: Optional[str] = None,
    results: Optional[Dict[str, Any]] = None,
    celery_task_id: Optional[str] = None,
) -> None:
    """Update a playbook execution record.

    Uses raw SQL so this module stays independent of any single
    service's ORM models.
    """
    import json

    sets = ["status = :status"]
    params: Dict[str, Any] = {"execution_id": execution_id, "status": status}

    if status == "running":
        sets.append("started_at = :started_at")
        params["started_at"] = _utcnow()

    if status in ("completed", "failed", "cancelled"):
        sets.append("completed_at = :completed_at")
        params["completed_at"] = _utcnow()

    if error_message is not None:
        sets.append("error_message = :error_message")
        params["error_message"] = error_message

    if results is not None:
        sets.append("result = :result")
        params["result"] = json.dumps(results)

    if celery_task_id is not None:
        sets.append("n8n_execution_id = :celery_task_id")
        params["celery_task_id"] = celery_task_id

    query = text(
        f"UPDATE playbook_executions SET {', '.join(sets)} WHERE id = :execution_id"
    )

    db.execute(query, params)
    db.commit()

    logger.debug(
        "Updated execution %s -> status=%s",
        execution_id,
        status,
    )
