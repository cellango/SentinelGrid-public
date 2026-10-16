"""Scheduled report generation service using APScheduler."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.orm import Session
from app.models.report import Report, ReportTemplate, ReportStatus, ReportFormat
from app.services.report_generator import ReportGeneratorService
from app.core.database import get_db
from app.services.audit_client import AuditClient

logger = logging.getLogger(__name__)


class ReportScheduler:
    """Manages scheduled report generation."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
        self.report_service = ReportGeneratorService()
        self.audit_client = AuditClient()
        logger.info("Report scheduler started")
    
    def schedule_report(
        self,
        template: ReportTemplate,
        tenant_id: str,
        schedule_config: Dict[str, Any],
        report_id: Optional[str] = None
    ) -> str:
        """
        Schedule a report based on template schedule configuration.
        
        Args:
            template: Report template
            tenant_id: Tenant ID
            schedule_config: Schedule configuration from template
            report_id: Optional report ID (for one-time schedules)
            
        Returns:
            Job ID
        """
        frequency = schedule_config.get('frequency', 'weekly')
        day = schedule_config.get('day')
        time = schedule_config.get('time', '09:00')
        enabled = schedule_config.get('enabled', True)
        
        if not enabled:
            logger.info(f"Schedule disabled for template {template.id}")
            return ""
        
        # Parse time
        hour, minute = map(int, time.split(':'))
        
        # Create job function
        async def generate_scheduled_report():
            try:
                db = next(get_db())
                try:
                    # Create report record
                    report = Report(
                        tenant_id=tenant_id,
                        template_id=template.id,
                        name=f"{template.name} - {datetime.utcnow().strftime('%Y-%m-%d')}",
                        format=ReportFormat.PDF,
                        status=ReportStatus.PENDING,
                        generated_by="system",
                        report_metadata={
                            "report_type": template.type,
                            "template_name": template.name,
                            "scheduled": True,
                        },
                    )
                    
                    # Set date range (last period based on frequency)
                    end_date = datetime.utcnow()
                    if frequency == 'daily':
                        start_date = end_date - timedelta(days=1)
                    elif frequency == 'weekly':
                        start_date = end_date - timedelta(days=7)
                    elif frequency == 'monthly':
                        start_date = end_date - timedelta(days=30)
                    else:
                        start_date = end_date - timedelta(days=7)
                    
                    report.date_range_start = start_date
                    report.date_range_end = end_date
                    
                    db.add(report)
                    db.commit()
                    db.refresh(report)
                    
                    # Generate report
                    await self.report_service.generate_report(
                        db,
                        report,
                        template,
                        tenant_id,
                        realm_name="scheduled_report",
                        date_range={
                            'start': start_date.isoformat(),
                            'end': end_date.isoformat()
                        },
                        report_parameters={},
                    )
                    
                    logger.info(f"Generated scheduled report {report.id} for tenant {tenant_id}")
                    
                    # Send email to recipients if configured
                    recipients = schedule_config.get('recipients', [])
                    if recipients:
                        from app.services.email_service import get_email_service
                        email_service = get_email_service()
                        delivered = await email_service.send_report_email(
                            report,
                            recipients,
                            subject=f"SentinelGrid Report: {template.name}",
                            message=f"Your scheduled {template.name} report is ready."
                        )
                        await self.audit_client.log_event({
                            "tenant_id": tenant_id,
                            "action": "report_schedule_delivery_attempted",
                            "action_category": "compliance",
                            "actor_user_id": "system",
                            "resource_type": "report",
                            "resource_id": report.id,
                            "resource_name": report.name,
                            "success": bool(delivered),
                            "metadata": {
                                "template_id": template.id,
                                "recipient_count": len(recipients),
                            },
                        })
                    
                finally:
                    db.close()
            
            except Exception as e:
                logger.error(f"Failed to generate scheduled report: {e}", exc_info=True)
        
        # Create trigger based on frequency
        if frequency == 'daily':
            trigger = CronTrigger(hour=hour, minute=minute)
        elif frequency == 'weekly':
            # day is day of week (monday, tuesday, etc.)
            day_map = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            day_of_week = day_map.get(day.lower() if day else 'monday', 0)
            trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute)
        elif frequency == 'monthly':
            # day is day of month (1-31)
            day_of_month = int(day) if day else 1
            trigger = CronTrigger(day=day_of_month, hour=hour, minute=minute)
        elif frequency == 'quarterly':
            # Run on provided day for Jan/Apr/Jul/Oct
            day_of_month = int(day) if day else 1
            trigger = CronTrigger(month='1,4,7,10', day=day_of_month, hour=hour, minute=minute)
        else:
            logger.warning(f"Unknown frequency: {frequency}, defaulting to weekly")
            trigger = CronTrigger(day_of_week=0, hour=hour, minute=minute)
        
        # Schedule job
        job_id = f"report_{template.id}_{tenant_id}"
        self.scheduler.add_job(
            generate_scheduled_report,
            trigger=trigger,
            id=job_id,
            replace_existing=True
        )
        
        logger.info(f"Scheduled report job {job_id} with trigger {trigger}")
        return job_id
    
    def unschedule_report(self, job_id: str):
        """Remove a scheduled report."""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed scheduled report job {job_id}")
        except Exception as e:
            logger.warning(f"Failed to remove job {job_id}: {e}")
    
    def list_scheduled_reports(self, tenant_id: Optional[str] = None) -> list:
        """List all scheduled report jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            if tenant_id is None or tenant_id in job.id:
                jobs.append({
                    'job_id': job.id,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
        return jobs
    
    def shutdown(self):
        """Shutdown the scheduler."""
        self.scheduler.shutdown()
        logger.info("Report scheduler shut down")


# Global scheduler instance
_scheduler: Optional[ReportScheduler] = None


def get_scheduler() -> ReportScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = ReportScheduler()
    return _scheduler
