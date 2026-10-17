"""Background scheduler for periodic rule evaluation."""

import logging
import asyncio
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[object] = None


def get_scheduler() -> object:
    """Read an initialized runtime; never construct a scheduler from a request."""
    if _scheduler is None:
        raise RuntimeError("Owned detection scheduler runtime unavailable")
    return _scheduler


def read_scheduler_status() -> dict:
    """Bounded projection of owned runtime state, not scheduling or readiness."""
    scheduler = get_scheduler()
    running = scheduler.running
    if type(running) is not bool:
        raise ValueError("Invalid scheduler state")
    jobs = scheduler.get_jobs()
    if not isinstance(jobs, list) or len(jobs) > 100:
        raise ValueError("Scheduler status exceeds read contract")
    result = []
    for job in jobs:
        if any(
            not isinstance(value, str)
            or not 1 <= len(value) <= 256
            or any(ord(c) < 32 or ord(c) == 127 for c in value)
            for value in (job.id, job.name)
        ):
            raise ValueError("Invalid scheduler job metadata")
        if job.next_run_time is not None and (
            not isinstance(job.next_run_time, datetime)
            or job.next_run_time.tzinfo is None
            or job.next_run_time.utcoffset() is None
        ):
            raise ValueError("Invalid scheduler next-run metadata")
        result.append(
            dict(
                id=job.id,
                name=job.name,
                next_run_time=job.next_run_time.isoformat()
                if job.next_run_time
                else None,
            )
        )
    return {"running": running, "jobs": result}


def _require_scheduler_authority():
    raise RuntimeError(
        "Owned detection scheduler workload, storage and effect contract required"
    )


async def evaluate_all_rules_job(tenant_id: Optional[str] = None):
    """
    Background job to evaluate all enabled rules.

    Args:
        tenant_id: Optional tenant ID to evaluate rules for (None = all tenants)
    """
    _require_scheduler_authority()
    from app.core.database import SessionLocal
    from app.engine.rule_engine import RuleEngine
    from app.services.alert_service import create_alerts

    db: Session = SessionLocal()
    try:
        logger.info(
            f"Starting scheduled rule evaluation for tenant: {tenant_id or 'all'}"
        )

        engine = RuleEngine(db)
        results = await engine.evaluate_all_rules(tenant_id)

        logger.info(
            f"Rule evaluation complete: {results['total_rules']} rules evaluated, "
            f"{results['alerts_generated']} alerts generated"
        )

        # Create alerts for all generated alerts
        all_alerts = []
        for rule_result in results.get("rule_results", []):
            alerts = rule_result.get("alerts", [])
            all_alerts.extend(alerts)

            # Get tenant_id from first alert if not provided
            if not tenant_id and alerts:
                tenant_id = alerts[0].get("tenant_id")

        if all_alerts and tenant_id:
            creation_result = await create_alerts(tenant_id, all_alerts)
            logger.info(
                f"Created {creation_result['created']} alerts, "
                f"{creation_result['failed']} failed"
            )

        return results

    except Exception as e:
        logger.error(f"Error in scheduled rule evaluation: {e}", exc_info=True)
        return None

    finally:
        db.close()


def start_scheduler(tenant_id: Optional[str] = None):
    """
    Start the background scheduler for periodic rule evaluation.

    Args:
        tenant_id: Optional tenant ID to evaluate rules for (None = all tenants)
    """
    _require_scheduler_authority()
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = get_scheduler()

    if scheduler.running:
        logger.warning("Scheduler is already running")
        return

    # Add job to evaluate all rules at configured interval
    interval_seconds = settings.EVALUATION_INTERVAL_SECONDS

    scheduler.add_job(
        evaluate_all_rules_job,
        trigger=IntervalTrigger(seconds=interval_seconds),
        args=[tenant_id],
        id="evaluate_all_rules",
        name="Evaluate All Detection Rules",
        replace_existing=True,
        max_instances=1,  # Prevent concurrent executions
    )

    scheduler.start()
    logger.info(
        f"Started rule evaluation scheduler with interval: {interval_seconds} seconds"
    )


def stop_scheduler():
    """Stop the background scheduler."""
    _require_scheduler_authority()
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Stopped rule evaluation scheduler")


def add_one_time_job(job_func, run_date: datetime, *args, **kwargs):
    """
    Add a one-time scheduled job.

    Args:
        job_func: Function to execute
        run_date: When to run the job
        *args: Positional arguments for job function
        **kwargs: Keyword arguments for job function
    """
    _require_scheduler_authority()
    scheduler = get_scheduler()
    scheduler.add_job(
        job_func,
        trigger="date",
        run_date=run_date,
        args=args,
        kwargs=kwargs,
    )
