"""
API endpoint tests for compliance platform
"""

import os
import sys
from datetime import datetime
from uuid import uuid4
import types

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text

# Make reporting_service modules importable for direct endpoint calls
REPORTING_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "services", "reporting_service"))
if REPORTING_ROOT not in sys.path:
    sys.path.insert(0, REPORTING_ROOT)
LIBS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "libs"))
if LIBS_ROOT not in sys.path:
    sys.path.insert(0, LIBS_ROOT)
# Lightweight stubs for apscheduler when it isn't installed in the test env
if "apscheduler" not in sys.modules:
    aps = types.ModuleType("apscheduler")
    schedulers_mod = types.ModuleType("apscheduler.schedulers")
    asyncio_mod = types.ModuleType("apscheduler.schedulers.asyncio")
    triggers_mod = types.ModuleType("apscheduler.triggers")
    cron_mod = types.ModuleType("apscheduler.triggers.cron")
    date_mod = types.ModuleType("apscheduler.triggers.date")

    class _DummyScheduler:
        def __init__(self, *args, **kwargs):
            self._jobs = []

        def start(self):
            return None

        def add_job(self, *args, **kwargs):
            # store minimal info for list_scheduled_reports if needed
            job_id = kwargs.get("id", "job")
            self._jobs.append(types.SimpleNamespace(id=job_id, next_run_time=None, trigger="dummy"))
            return None

        def get_jobs(self):
            return list(self._jobs)

        def remove_job(self, job_id):
            self._jobs = [j for j in self._jobs if j.id != job_id]

    class _DummyTrigger:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def __str__(self):
            return "dummy-trigger"

    asyncio_mod.AsyncIOScheduler = _DummyScheduler
    cron_mod.CronTrigger = _DummyTrigger
    date_mod.DateTrigger = _DummyTrigger

    aps.schedulers = schedulers_mod
    aps.triggers = triggers_mod
    sys.modules["apscheduler"] = aps
    sys.modules["apscheduler.schedulers"] = schedulers_mod
    sys.modules["apscheduler.schedulers.asyncio"] = asyncio_mod
    sys.modules["apscheduler.triggers"] = triggers_mod
    sys.modules["apscheduler.triggers.cron"] = cron_mod
    sys.modules["apscheduler.triggers.date"] = date_mod

from app.api import reports as reports_api  # type: ignore
from app.api import scheduled_reports as scheduled_api  # type: ignore


@pytest.fixture
def mock_jwt_token(tenant_a, test_user_a):
    """Mock JWT token with tenant claims."""
    return {
        "sub": test_user_a["id"],
        "email": test_user_a["email"],
        "tenant_id": str(tenant_a["id"]),
        "realm": tenant_a["realm"],
        "realm_access": {
            "roles": test_user_a["roles"]
        }
    }


class TestAuditLogsAPI:
    """Test Audit Logs API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_audit_logs(self, db_session, tenant_a):
        """Test GET /api/v1/audit/logs endpoint."""
        # Create test audit log
        db_session.execute(
            text("""
                INSERT INTO platform_audit_logs (tenant_id, realm_name, action, actor_user_id)
                VALUES (:tenant_id, :realm_name, 'test_action', 'test_user')
            """),
            {"tenant_id": str(tenant_a["id"]), "realm_name": tenant_a["realm"]}
        )
        db_session.commit()
        
        # This test would use TestClient to call the API
        # Placeholder for actual API test
        assert True
    
    @pytest.mark.asyncio
    async def test_export_audit_logs(self, db_session, tenant_a):
        """Test GET /api/v1/audit/export endpoint."""
        # Test exporting audit logs to CSV
        # Would use TestClient in actual implementation
        assert True


class TestReportsAPI:
    """Test Reports API endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_reports_tenant_scoped(self, db_session, tenant_a, tenant_b):
        """Test GET /api/v1/reports returns only tenant's reports."""
        report_a_id = uuid4()
        report_b_id = uuid4()
        
        # Create reports for both tenants
        for report_id, tenant in [(report_a_id, tenant_a), (report_b_id, tenant_b)]:
            db_session.execute(
                text("""
                    INSERT INTO generated_reports (id, tenant_id, realm_name, report_type, report_name, status)
                    VALUES (:id, :tenant_id, :realm_name, 'soc2_coverage', :report_name, 'ready')
                """),
                {
                    "id": str(report_id),
                    "tenant_id": str(tenant["id"]),
                    "realm_name": tenant["realm"],
                    "report_name": f"Report_{tenant['name']}.pdf"
                }
            )
        
        db_session.commit()
        
        # Query as Tenant A
        result = db_session.execute(
            text("""
                SELECT report_name FROM generated_reports
                WHERE tenant_id = :tenant_id AND realm_name = :realm_name
            """),
            {"tenant_id": str(tenant_a["id"]), "realm_name": tenant_a["realm"]}
        )
        
        reports = [row[0] for row in result.fetchall()]
        
        # Should only see Tenant A's report
        assert any("Acme Corp" in r for r in reports)
        assert not any("TechStart" in r for r in reports), "Cross-tenant leak!"
    
    @pytest.mark.asyncio
    async def test_download_report_authorization(self):
        """Test that download endpoint checks tenant authorization."""
        # This would test the actual API endpoint
        # Should return 404 if tenant doesn't match
        # Should return file if tenant matches
        assert True
    
    @pytest.mark.asyncio
    async def test_generate_report_api(self):
        """Test POST /api/v1/reports/generate endpoint."""
        # Test report generation API
        # Should:
        # 1. Validate request
        # 2. Create report record with 'generating' status
        # 3. Trigger async generation
        # 4. Return report_id
        assert True

    @pytest.mark.asyncio
    async def test_list_reports_api_is_tenant_scoped(self, db_session, tenant_a, tenant_b):
        """Directly call reporting_service list_reports and ensure cross-tenant data is hidden."""
        report_a_id = str(uuid4())
        report_b_id = str(uuid4())
        try:
            # Insert two reports into reporting schema (one per tenant)
            db_session.execute(
                text("""
                    INSERT INTO reporting.reports (id, tenant_id, name, format, status)
                    VALUES (:id, :tenant_id, :name, 'PDF', 'COMPLETED')
                """),
                {"id": report_a_id, "tenant_id": str(tenant_a["id"]), "name": "TenantA SOC2"}
            )
            db_session.execute(
                text("""
                    INSERT INTO reporting.reports (id, tenant_id, name, format, status)
                    VALUES (:id, :tenant_id, :name, 'PDF', 'COMPLETED')
                """),
                {"id": report_b_id, "tenant_id": str(tenant_b["id"]), "name": "TenantB SOC2"}
            )

            results = await reports_api.list_reports(
                limit=10,
                offset=0,
                status_filter=None,
                tenant_id=str(tenant_a["id"]),
                db=db_session
            )
            ids = {r.id for r in results}
            assert report_a_id in ids
            assert report_b_id not in ids
        finally:
            db_session.rollback()

    @pytest.mark.asyncio
    async def test_get_report_other_tenant_returns_404(self, db_session, tenant_a, tenant_b):
        """Ensure fetching a report by ID enforces tenant ownership."""
        report_b_id = str(uuid4())
        try:
            db_session.execute(
                text("""
                    INSERT INTO reporting.reports (id, tenant_id, name)
                    VALUES (:id, :tenant_id, :name)
                """),
                {"id": report_b_id, "tenant_id": str(tenant_b["id"]), "name": "TenantB Only"}
            )

            with pytest.raises(HTTPException) as exc:
                await reports_api.get_report(report_id=report_b_id, tenant_id=str(tenant_a["id"]), db=db_session)
            assert exc.value.status_code == 404
        finally:
            db_session.rollback()


class TestScheduleAPI:
    """Test report schedule API endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_schedule(self, db_session, tenant_a):
        """Test creating a report schedule."""
        schedule_id = uuid4()
        
        db_session.execute(
            text("""
                INSERT INTO report_schedules (
                    id, tenant_id, realm_name, report_type, schedule_name,
                    cron_expression, recipients, is_active, created_by
                )
                VALUES (:id, :tenant_id, :realm_name, :report_type, :name, :cron, :recipients, :active, :created_by)
            """),
            {
                "id": str(schedule_id),
                "tenant_id": str(tenant_a["id"]),
                "realm_name": tenant_a["realm"],
                "report_type": "iam_mfa_hygiene",
                "name": "Monthly IAM Report",
                "cron": "0 9 1 * *",
                "recipients": ["compliance@acme.com"],
                "active": True,
                "created_by": "admin@acme.com"
            }
        )
        
        db_session.commit()
        
        # Verify schedule
        result = db_session.execute(
            text("SELECT schedule_name, cron_expression, is_active FROM report_schedules WHERE id = :id"),
            {"id": str(schedule_id)}
        )
        
        schedule = result.fetchone()
        assert schedule is not None
        assert schedule[0] == "Monthly IAM Report"
        assert schedule[1] == "0 9 1 * *"
        assert schedule[2] is True

    @pytest.mark.asyncio
    async def test_list_schedulable_templates_filters_other_tenants(self, db_session, tenant_a, tenant_b):
        """Only tenant-owned templates are schedulable; shared rows remain browse-only."""
        system_template_id = str(uuid4())
        tenant_a_template_id = str(uuid4())
        tenant_b_template_id = str(uuid4())
        try:
            db_session.execute(
                text("""
                    INSERT INTO reporting.report_templates (id, tenant_id, name, description, type, sections, data_queries, schedule, required_roles, created_at, updated_at)
                    VALUES (:id, NULL, 'System SOC2', '', 'soc2', '[]', '[]', NULL, '[]', NOW(), NOW())
                """),
                {"id": system_template_id}
            )
            db_session.execute(
                text("""
                    INSERT INTO reporting.report_templates (id, tenant_id, name, description, type, sections, data_queries, schedule, required_roles, created_at, updated_at)
                    VALUES (:id, :tenant_id, 'TenantA SOC2', '', 'soc2', '[]', '[]', NULL, '[]', NOW(), NOW())
                """),
                {"id": tenant_a_template_id, "tenant_id": str(tenant_a["id"])}
            )
            db_session.execute(
                text("""
                    INSERT INTO reporting.report_templates (id, tenant_id, name, description, type, sections, data_queries, schedule, required_roles, created_at, updated_at)
                    VALUES (:id, :tenant_id, 'TenantB SOC2', '', 'soc2', '[]', '[]', NULL, '[]', NOW(), NOW())
                """),
                {"id": tenant_b_template_id, "tenant_id": str(tenant_b["id"])}
            )

            templates = await scheduled_api.list_schedulable_templates(
                type_filter="soc2",
                tenant_id=str(tenant_a["id"]),
                db=db_session
            )
            ids = {tpl["id"] for tpl in templates}
            assert system_template_id not in ids
            assert tenant_a_template_id in ids
            assert tenant_b_template_id not in ids
        finally:
            db_session.rollback()

    @pytest.mark.asyncio
    async def test_create_schedule_blocks_cross_tenant_template(self, db_session, tenant_a, tenant_b, monkeypatch):
        """Scheduler should reject shared or cross-tenant templates."""
        system_template_id = str(uuid4())
        tenant_b_template_id = str(uuid4())
        tenant_a_template_id = str(uuid4())

        class StubScheduler:
            def __init__(self):
                self.scheduled = []

            def schedule_report(self, template, tenant_id, schedule):
                self.scheduled.append((template.id, tenant_id, schedule))
                return f"job_{template.id}_{tenant_id}"

            def list_scheduled_reports(self, tenant_id):
                return []

            def unschedule_report(self, job_id):
                self.unscheduled = job_id

        stub = StubScheduler()
        monkeypatch.setattr(scheduled_api, "get_scheduler", lambda: stub)

        try:
            db_session.execute(
                text("""
                    INSERT INTO reporting.report_templates (id, tenant_id, name, description, type, sections, data_queries, schedule, required_roles, created_at, updated_at)
                    VALUES (:id, NULL, 'System SOC2', '', 'soc2', '[]', '[]', NULL, '[]', NOW(), NOW())
                """),
                {"id": system_template_id}
            )
            db_session.execute(
                text("""
                    INSERT INTO reporting.report_templates (id, tenant_id, name, description, type, sections, data_queries, schedule, required_roles, created_at, updated_at)
                    VALUES (:id, :tenant_id, 'TenantB SOC2', '', 'soc2', '[]', '[]', NULL, '[]', NOW(), NOW())
                """),
                {"id": tenant_b_template_id, "tenant_id": str(tenant_b["id"])}
            )
            db_session.execute(
                text("""
                    INSERT INTO reporting.report_templates (id, tenant_id, name, description, type, sections, data_queries, schedule, required_roles, created_at, updated_at)
                    VALUES (:id, :tenant_id, 'TenantA SOC2', '', 'soc2', '[]', '[]', NULL, '[]', NOW(), NOW())
                """),
                {"id": tenant_a_template_id, "tenant_id": str(tenant_a["id"])}
            )

            with pytest.raises(HTTPException) as exc:
                await scheduled_api.create_scheduled_report(
                    request={
                        "template_id": system_template_id,
                        "schedule": {"frequency": "weekly", "day": "monday", "time": "09:00", "recipients": ["a@example.com"], "enabled": True},
                        "recipients": ["a@example.com"]
                    },
                    tenant_id=str(tenant_a["id"]),
                    db=db_session
                )
            assert exc.value.status_code == 403

            with pytest.raises(HTTPException) as exc:
                await scheduled_api.create_scheduled_report(
                    request={
                        "template_id": tenant_b_template_id,
                        "schedule": {"frequency": "weekly", "day": "monday", "time": "09:00", "recipients": ["a@example.com"], "enabled": True},
                        "recipients": ["a@example.com"]
                    },
                    tenant_id=str(tenant_a["id"]),
                    db=db_session
                )
            assert exc.value.status_code == 403

            response = await scheduled_api.create_scheduled_report(
                request={
                    "template_id": tenant_a_template_id,
                    "schedule": {"frequency": "weekly", "day": "monday", "time": "09:00", "recipients": ["a@example.com"], "enabled": True},
                    "recipients": ["a@example.com"]
                },
                tenant_id=str(tenant_a["id"]),
                db=db_session
            )
            assert response["job_id"].startswith(f"job_{tenant_a_template_id}")
            assert stub.scheduled, "Stub scheduler should have been invoked for allowed tenant"
        finally:
            db_session.execute(
                text("DELETE FROM reporting.report_templates WHERE id IN (:system_id, :a, :b)"),
                {"system_id": system_template_id, "a": tenant_a_template_id, "b": tenant_b_template_id}
            )
            db_session.commit()


class TestLLMQueryAPI:
    """Test LLM query API endpoint."""
    
    @pytest.mark.asyncio
    async def test_query_reports_api(
        self,
        mock_embedding_model,
        tenant_a,
        test_user_a
    ):
        """Test POST /api/v1/reports/query endpoint."""
        from backend.services.model_gateway.app.services.report_qa_service import (
            ReportQAService,
            UserContext
        )
        
        service = ReportQAService(
            embedding_model=mock_embedding_model
        )
        
        user_context = UserContext(
            user_id=test_user_a["id"],
            tenant_id=tenant_a["id"],
            realm=tenant_a["realm"]
        )
        
        # Query
        result = service.query_reports(user_context, "What is our compliance score?")
        
        # Verify response
        assert result.get("error") == "Service unavailable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
