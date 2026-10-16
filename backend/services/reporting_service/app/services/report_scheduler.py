"""
Report Scheduler
Schedules automated compliance report generation using APScheduler
"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID

logger = logging.getLogger(__name__)

# Try importing APScheduler
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    logger.warning("APScheduler not available, report scheduling will be disabled")
    APSCHEDULER_AVAILABLE = False


class ReportScheduler:
    """Automated report generation scheduler."""
    
    def __init__(self):
        """Initialize report scheduler."""
        if not APSCHEDULER_AVAILABLE:
            logger.warning("APScheduler not available, scheduler disabled")
            self.scheduler = None
            return
        
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        logger.info("Report scheduler started")
    
    def schedule_report(
        self,
        schedule_id: UUID,
        tenant_id: UUID,
        realm_name: str,
        report_type: str,
        cron_expression: str,
        timezone: str = 'UTC'
    ):
        """
        Schedule a report for automated generation.
        
        Args:
            schedule_id: Schedule ID
            tenant_id: Tenant ID
            realm_name: Realm name
            report_type: Type of report
            cron_expression: Cron expression (e.g., '0 9 * * MON')
            timezone: Timezone for scheduling
        """
        if not self.scheduler:
            logger.warning("Scheduler not available, cannot schedule report")
            return
        
        job_id = f"report_{schedule_id}"
        
        try:
            # Remove existing job if any
            self.scheduler.remove_job(job_id)
        except:
            pass
        
        # Add new job
        self.scheduler.add_job(
            func=self._generate_scheduled_report,
            trigger=CronTrigger.from_crontab(cron_expression, timezone=timezone),
            args=[schedule_id, tenant_id, realm_name, report_type],
            id=job_id,
            name=f"Report: {report_type} for {tenant_id}",
            replace_existing=True,
            misfire_grace_time=3600  # 1 hour grace period
        )
        
        logger.info(f"Scheduled report {report_type} for tenant {tenant_id} with cron: {cron_expression}")
    
    def unschedule_report(self, schedule_id: UUID):
        """
        Remove a scheduled report.
        
        Args:
            schedule_id: Schedule ID to remove
        """
        if not self.scheduler:
            return
        
        job_id = f"report_{schedule_id}"
        
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Unscheduled report: {schedule_id}")
        except Exception as e:
            logger.warning(f"Failed to unschedule report {schedule_id}: {e}")
    
    def get_next_run_time(self, schedule_id: UUID) -> Optional[datetime]:
        """
        Get next run time for a scheduled report.
        
        Args:
            schedule_id: Schedule ID
            
        Returns:
            Next run time or None
        """
        if not self.scheduler:
            return None
        
        job_id = f"report_{schedule_id}"
        
        try:
            job = self.scheduler.get_job(job_id)
            if job and job.next_run_time:
                return job.next_run_time
        except:
            pass
        
        return None
    
    def list_scheduled_reports(self) -> List[dict]:
        """
        List all scheduled reports.
        
        Returns:
            List of scheduled job info
        """
        if not self.scheduler:
            return []
        
        jobs = []
        for job in self.scheduler.get_jobs():
            if job.id.startswith("report_"):
                jobs.append({
                    "job_id": job.id,
                    "schedule_id": job.id.replace("report_", ""),
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger)
                })
        
        return jobs
    
    def _generate_scheduled_report(
        self,
        schedule_id: UUID,
        tenant_id: UUID,
        realm_name: str,
        report_type: str
    ):
        """
        Generate a scheduled report (called by scheduler).
        
        This is a placeholder - actual implementation should import and call
        the report generation service.
        
        Args:
            schedule_id: Schedule ID
            tenant_id: Tenant ID
            realm_name: Realm name
            report_type: Type of report
        """
        logger.info(f"Generating scheduled report: {report_type} for tenant {tenant_id}")
        
        try:
            # Import here to avoid circular dependencies
            from app.services.report_generator import generate_report
            from app.core.database import SessionLocal
            
            # Generate report
            db = SessionLocal()
            try:
                report = generate_report(
                    db=db,
                    tenant_id=tenant_id,
                    realm_name=realm_name,
                    report_type=report_type,
                    generated_by='system'
                )
                
                logger.info(f"Scheduled report generated successfully: {report.id}")
                
                # Update schedule status
                from sqlalchemy import text
                db.execute(
                    text("""
                        UPDATE report_schedules
                        SET last_run_at = NOW(),
                            last_run_status = 'success',
                            last_report_id = :report_id,
                            next_run_at = :next_run
                        WHERE id = :schedule_id
                    """),
                    {
                        "schedule_id": str(schedule_id),
                        "report_id": str(report.id),
                        "next_run": self.get_next_run_time(schedule_id)
                    }
                )
                db.commit()
                
                # Send email to recipients (implement in email service)
                # self._send_report_email(schedule_id, report)
                
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Failed to generate scheduled report: {e}", exc_info=True)
            
            # Update schedule with failure status
            try:
                from app.core.database import SessionLocal
                from sqlalchemy import text
                
                db = SessionLocal()
                try:
                    db.execute(
                        text("""
                            UPDATE report_schedules
                            SET last_run_at = NOW(),
                                last_run_status = 'failed'
                            WHERE id = :schedule_id
                        """),
                        {"schedule_id": str(schedule_id)}
                    )
                    db.commit()
                finally:
                    db.close()
            except:
                pass
    
    def shutdown(self):
        """Shutdown the scheduler."""
        if self.scheduler:
            self.scheduler.shutdown()
            logger.info("Report scheduler shut down")


# Singleton
_report_scheduler: Optional[ReportScheduler] = None


def get_scheduler() -> ReportScheduler:
    """Get or create the global report scheduler instance."""
    global _report_scheduler
    if _report_scheduler is None:
        _report_scheduler = ReportScheduler()
    return _report_scheduler

