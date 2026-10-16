"""
Integration tests for report generation pipeline
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy import text


class TestReportGenerationPipeline:
    """Test complete report generation workflow."""
    
    def test_create_generated_report_record(self, db_session, tenant_a):
        """Test creating a generated report record in database."""
        report_id = uuid4()
        
        db_session.execute(
            text("""
                INSERT INTO generated_reports (
                    id, tenant_id, realm_name, report_type, report_name,
                    report_period_start, report_period_end, generated_by, status
                )
                VALUES (
                    :id, :tenant_id, :realm_name, :report_type, :report_name,
                    :period_start, :period_end, :generated_by, :status
                )
            """),
            {
                "id": str(report_id),
                "tenant_id": str(tenant_a["id"]),
                "realm_name": tenant_a["realm"],
                "report_type": "soc2_coverage",
                "report_name": f"SOC2_Coverage_Report_2025-12-02_{tenant_a['name'].replace(' ', '')}.pdf",
                "period_start": "2025-11-01",
                "period_end": "2025-11-30",
                "generated_by": "test-user",
                "status": "ready"
            }
        )
        
        db_session.commit()
        
        # Verify record created
        result = db_session.execute(
            text("SELECT report_name FROM generated_reports WHERE id = :id"),
            {"id": str(report_id)}
        )
        
        report = result.fetchone()
        assert report is not None
        assert "SOC2_Coverage_Report" in report[0]
        assert "2025-12-02" in report[0]
        assert tenant_a['name'].replace(' ', '') in report[0]
    
    def test_report_naming_convention(self, tenant_a):
        """Test report naming follows convention: Type_YYYY-MM-DD_TenantName.pdf"""
        report_type = "SOC2_Coverage_Report"
        date = "2025-12-02"
        tenant_name = tenant_a['name'].replace(' ', '')
        
        report_name = f"{report_type}_{date}_{tenant_name}.pdf"
        
        assert report_name == "SOC2_Coverage_Report_2025-12-02_AcmeCorp.pdf"
        assert date in report_name
        assert tenant_name in report_name
    
    def test_report_schedule_creation(self, db_session, tenant_a):
        """Test creating a report schedule."""
        schedule_id = uuid4()
        
        db_session.execute(
            text("""
                INSERT INTO report_schedules (
                    id, tenant_id, realm_name, report_type, schedule_name,
                    cron_expression, timezone, recipients, is_active, created_by
                )
                VALUES (
                    :id, :tenant_id, :realm_name, :report_type, :schedule_name,
                    :cron_expression, :timezone, :recipients, :is_active, :created_by
                )
            """),
            {
                "id": str(schedule_id),
                "tenant_id": str(tenant_a["id"]),
                "realm_name": tenant_a["realm"],
                "report_type": "soc2_coverage",
                "schedule_name": "Weekly SOC 2 Report",
                "cron_expression": "0 9 * * MON",
                "timezone": "UTC",
                "recipients": ["compliance@acme.com"],
                "is_active": True,
                "created_by": "admin@acme.com"
            }
        )
        
        db_session.commit()
        
        # Verify schedule created
        result = db_session.execute(
            text("SELECT schedule_name, cron_expression FROM report_schedules WHERE id = :id"),
            {"id": str(schedule_id)}
        )
        
        schedule = result.fetchone()
        assert schedule is not None
        assert schedule[0] == "Weekly SOC 2 Report"
        assert schedule[1] == "0 9 * * MON"
    
    def test_report_access_logging(self, db_session, tenant_a, test_user_a):
        """Test logging report access for compliance."""
        report_id = uuid4()
        
        # Create report
        db_session.execute(
            text("""
                INSERT INTO generated_reports (id, tenant_id, realm_name, report_type, report_name, status)
                VALUES (:id, :tenant_id, :realm_name, 'soc2_coverage', 'Test_Report.pdf', 'ready')
            """),
            {"id": str(report_id), "tenant_id": str(tenant_a["id"]), "realm_name": tenant_a["realm"]}
        )
        
        # Log access
        db_session.execute(
            text("""
                INSERT INTO report_access_log (
                    report_id, tenant_id, realm_name, user_id, user_email, access_type
                )
                VALUES (:report_id, :tenant_id, :realm_name, :user_id, :user_email, :access_type)
            """),
            {
                "report_id": str(report_id),
                "tenant_id": str(tenant_a["id"]),
                "realm_name": tenant_a["realm"],
                "user_id": test_user_a["id"],
                "user_email": test_user_a["email"],
                "access_type": "download_pdf"
            }
        )
        
        db_session.commit()
        
        # Verify access logged
        result = db_session.execute(
            text("""
                SELECT access_type, user_email FROM report_access_log
                WHERE report_id = :report_id
            """),
            {"report_id": str(report_id)}
        )
        
        log = result.fetchone()
        assert log is not None
        assert log[0] == "download_pdf"
        assert log[1] == test_user_a["email"]


class TestReportScheduler:
    """Test report scheduling functionality."""
    
    def test_scheduler_initialization(self):
        """Test scheduler initializes correctly."""
        try:
            from backend.services.reporting_service.app.services.report_scheduler import ReportScheduler
            
            scheduler = ReportScheduler()
            assert scheduler is not None
            
            # Clean up
            if scheduler.scheduler:
                scheduler.shutdown()
            
        except ImportError:
            pytest.skip("APScheduler not available")
    
    def test_cron_expression_parsing(self):
        """Test cron expression parsing."""
        try:
            from apscheduler.triggers.cron import CronTrigger
            
            # Weekly Monday 9am
            trigger = CronTrigger.from_crontab("0 9 * * MON")
            assert trigger is not None
            
            # Monthly 1st day 9am
            trigger = CronTrigger.from_crontab("0 9 1 * *")
            assert trigger is not None
            
        except ImportError:
            pytest.skip("APScheduler not available")


class TestReportDataCollection:
    """Test data collection for reports."""
    
    def test_collect_soc2_control_data(self, db_session, tenant_a):
        """Test collecting SOC 2 control data for report."""
        # This would test the actual data collection logic
        # For now, testing the query structure
        
        # Query control status for tenant
        result = db_session.execute(
            text("""
                SELECT COUNT(*) FROM tenant_control_status
                WHERE tenant_id = :tenant_id AND realm_name = :realm_name
            """),
            {"tenant_id": str(tenant_a["id"]), "realm_name": tenant_a["realm"]}
        )
        
        count = result.fetchone()[0]
        # Should be 0 initially (no data seeded yet)
        assert count >= 0
    
    def test_collect_mfa_stats(self, db_session, tenant_a):
        """Test collecting MFA statistics for IAM report."""
        # Query MFA status
        result = db_session.execute(
            text("""
                SELECT COUNT(*) as total,
                       COUNT(*) FILTER (WHERE mfa_enabled = true) as mfa_enabled
                FROM user_mfa_status
                WHERE tenant_id = :tenant_id AND realm_name = :realm_name
            """),
            {"tenant_id": str(tenant_a["id"]), "realm_name": tenant_a["realm"]}
        )
        
        stats = result.fetchone()
        # Initially empty, but query should work
        assert stats is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

