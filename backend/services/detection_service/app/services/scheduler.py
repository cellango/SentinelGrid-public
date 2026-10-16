"""Background scheduler for periodic rule evaluation."""

import logging
import asyncio
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.engine.rule_engine import RuleEngine
from app.services.alert_service import create_alerts
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def evaluate_all_rules_job(tenant_id: Optional[str] = None):
    """
    Background job to evaluate all enabled rules.
    
    Args:
        tenant_id: Optional tenant ID to evaluate rules for (None = all tenants)
    """
    db: Session = SessionLocal()
    try:
        logger.info(f"Starting scheduled rule evaluation for tenant: {tenant_id or 'all'}")
        
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
    # Temporarily disable rule evaluation until detection_rules schema aligns with model
    logger.info("Skipping scheduler start (detection_rules schema mismatch); enable after schema alignment")
    return
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
    scheduler = get_scheduler()
    scheduler.add_job(
        job_func,
        trigger="date",
        run_date=run_date,
        args=args,
        kwargs=kwargs,
    )
